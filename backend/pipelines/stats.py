# Path: ffbPlayerDraftingApp/backend/pipelines/stats.py

import datetime
import pandas as pd

from backend.data_sources.historical import fetch_last_year_weekly_stats
from backend.logging_config import log
from backend.settings import settings
from backend.storage.file_store import load_json, save_json
from backend.transforms.compute_ppg import calculate_top_n_games_avg
from backend.transforms.normalize import calculate_z_scores
from backend.utils import create_hybrid_slug_map


def run_stats(date_str: str | None = None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    log.info("Starting stats pipeline.", extra={"date": date_str})

    input_path = settings.DATA_DIR / date_str / "players_enriched.json"
    output_path = settings.DATA_DIR / date_str / "players_with_ppg.json"
    try:
        df = pd.DataFrame(load_json(input_path))
        cfg = settings.league_config

        hist_scores = fetch_last_year_weekly_stats()
        canonical_slugs = df["slug"].dropna().unique().tolist()
        mapped_hist_scores = create_hybrid_slug_map(hist_scores, canonical_slugs)

        df["top_n_avg"] = calculate_top_n_games_avg(
            df["slug"], mapped_hist_scores, cfg.top_game_count
        )
        df["projected_ppg"] = df["projected_points"] / cfg.games_divisor

        # Pass a copy of the DataFrame to prevent any potential side effects
        df["z_proj"] = calculate_z_scores(df.copy(), "projected_ppg")
        df["z_hist"] = calculate_z_scores(df.copy(), "top_n_avg")

        # --- NEW SCORING LOGIC ---
        log.info("Applying new scoring logic with targeted player boost.")

        # Define conditions for clarity
        has_projection = df["z_proj"].notna()
        has_history = df["z_hist"].notna()

        # Initialize score column
        df["score"] = 0.0

        # Case 1: Player has both projection and historical data
        df.loc[has_projection & has_history, "score"] = (
            df["z_proj"] * cfg.weight_projection
        ) + (df["z_hist"] * cfg.weight_last_year)

        # Case 2: Player only has historical data (e.g., retired but in system)
        df.loc[~has_projection & has_history, "score"] = df["z_hist"]

        # Case 3: Player only has projection data (e.g., rookies) -
        # Apply the projection weight to put them on the same scale as veterans.
        df.loc[has_projection & ~has_history, "score"] = (
            df["z_proj"] * cfg.weight_projection
        )
        # --- NEW PLAYER BOOST LOGIC ---
        # Load the list of players to boost
        boost_list_path = settings.BASE_DIR / "player_boost.json"
        if boost_list_path.exists():
            boost_data = load_json(boost_list_path)
            slugs_to_boost = boost_data.get("player_slugs", [])
            log.info(
                f"Loaded {len(slugs_to_boost)} players to boost from player_boost.json."
            )

            # Create a boolean mask for players who are in the boost list
            is_boosted_player = df["slug"].isin(slugs_to_boost)

            # Apply the boost
            boost_factor = 1 + cfg.player_boost
            df.loc[is_boosted_player, "score"] *= boost_factor
            log.info(
                f"Applied a {cfg.player_boost:.0%} boost to {is_boosted_player.sum()} players."
            )
            # Log the players who were boosted for verification
            log.info(f"Boosted players: {df.loc[is_boosted_player, 'slug'].tolist()}")
        else:
            log.warning("player_boost.json not found. Skipping player boost.")

        max_raw_score = df["score"].max()
        target_max_ppg = 25.0
        scaling_factor = target_max_ppg / max_raw_score if max_raw_score > 0 else 0
        df["expected_ppg"] = df["score"] * scaling_factor

        log.info("Scaling complete.", extra={"max_ppg": df["expected_ppg"].max()})
        # Add this line right before save_json(...)
        log.info(
            f"Final check before saving. Data for Ja'Marr Chase:\n{df[df['slug'] == 'jamarr-chase'][['slug', 'top_n_avg', 'z_hist', 'expected_ppg']].to_string()}"
        )
        save_json(output_path, df.to_dict(orient="records"))
        log.info("Stats pipeline completed successfully.")
    except Exception as e:
        log.exception("Stats pipeline failed.", extra={"error": str(e)})
        raise
