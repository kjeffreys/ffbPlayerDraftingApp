# Path: ffbPlayerDraftingApp/backend/pipelines/stats.py (FINAL)

import datetime
import pandas as pd
import numpy as np

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

        # --- Calculate Historical and Projection PPG ---
        hist_scores = fetch_last_year_weekly_stats()
        canonical_slugs = df["slug"].dropna().unique().tolist()
        mapped_hist_scores = create_hybrid_slug_map(hist_scores, canonical_slugs)

        df["top_n_avg"] = calculate_top_n_games_avg(
            df["slug"], mapped_hist_scores, cfg.top_game_count
        )
        df["projected_ppg"] = df["projected_points"] / cfg.games_divisor

        # --- Calculate Positional Z-Scores (using defensive copy) ---
        df["z_proj"] = calculate_z_scores(df.copy(), "projected_ppg")
        df["z_hist"] = calculate_z_scores(df.copy(), "top_n_avg")

        # --- FINAL SCORING LOGIC (Scale First, Then Blend) ---
        log.info("Applying final scoring logic (Scale First, Then Blend).")

        # Step 1: Create scaled versions of historical and projection scores independently
        max_z_hist = df["z_hist"].max()
        scaling_factor_hist = 25.0 / max_z_hist if max_z_hist > 0 else 0
        df["scaled_hist"] = df["z_hist"] * scaling_factor_hist

        max_z_proj = df["z_proj"].max()
        scaling_factor_proj = 25.0 / max_z_proj if max_z_proj > 0 else 0
        df["scaled_proj"] = df["z_proj"] * scaling_factor_proj
        log.info(
            "Created independent scaled scores for historical and projection data."
        )

        # Step 2: Use np.select for a clean, conditional blend of the scaled scores
        conditions = [
            df["scaled_proj"].notna() & df["scaled_hist"].notna(),  # Has both
            df["scaled_proj"].notna(),  # Has only projection
            df["scaled_hist"].notna(),  # Has only history
        ]
        choices = [
            (df["scaled_proj"] * cfg.weight_projection)
            + (df["scaled_hist"] * cfg.weight_last_year),
            df["scaled_proj"],
            df["scaled_hist"],
        ]
        df["score"] = np.select(conditions, choices, default=0.0)

        # Step 3: Apply the targeted player boost
        boost_list_path = settings.BASE_DIR.parent / "player_boost.json"
        if boost_list_path.exists():
            boost_data = load_json(boost_list_path)
            slugs_to_boost = boost_data.get("player_slugs", [])
            log.info(
                f"Loaded {len(slugs_to_boost)} players to boost from player_boost.json."
            )

            is_boosted_player = df["slug"].isin(slugs_to_boost)
            boost_factor = 1 + cfg.player_boost
            df.loc[is_boosted_player, "score"] *= boost_factor

            log.info(
                f"Applied a {cfg.player_boost:.0%} boost to {is_boosted_player.sum()} players."
            )
            log.info(f"Boosted players: {df.loc[is_boosted_player, 'slug'].tolist()}")
        else:
            log.warning("player_boost.json not found. Skipping player boost.")

        # The final score is our expected_ppg
        df["expected_ppg"] = df["score"]
        log.info("Final 'expected_ppg' calculation complete.")

        # Final diagnostic check
        log.info(
            f"Final check before saving. Data for Ja'Marr Chase:\n{df[df['slug'] == 'jamarr-chase'][['slug', 'scaled_hist', 'scaled_proj', 'expected_ppg']].to_string()}"
        )

        save_json(output_path, df.to_dict(orient="records"))
        log.info("Stats pipeline completed successfully.")
    except Exception as e:
        log.exception("Stats pipeline failed.", extra={"error": str(e)})
        raise
