# Path: ffbPlayerDraftingApp/backend/pipelines/stats.py (DEFINITIVE FINAL VERSION)

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

        # --- THIS IS THE FIX ---
        # A value of 0.0 in 'top_n_avg' for players with no history (rookies)
        # was causing them to be misclassified as underperforming veterans.
        # Replacing 0.0 with NaN ensures they are correctly identified as rookies
        # so that only their projection data is used for scoring.
        df["top_n_avg"] = df["top_n_avg"].replace(0.0, np.nan)
        # --- END OF FIX ---

        df["projected_ppg"] = df["projected_points"] / cfg.games_divisor

        # --- Calculate Positional Z-Scores ---
        df["z_proj"] = calculate_z_scores(df, "projected_ppg")
        df["z_hist"] = calculate_z_scores(df, "top_n_avg")

        # --- FINAL SCORING LOGIC (Scale First, Then Blend) ---
        log.info("Applying final scoring logic (Scale First, Then Blend).")
        max_z_hist = df["z_hist"].max()
        scaling_factor_hist = 25.0 / max_z_hist if max_z_hist > 0 else 0
        df["scaled_hist"] = df["z_hist"] * scaling_factor_hist
        max_z_proj = df["z_proj"].max()
        scaling_factor_proj = 25.0 / max_z_proj if max_z_proj > 0 else 0
        df["scaled_proj"] = df["z_proj"] * scaling_factor_proj
        log.info(
            "Created independent scaled scores for historical and projection data."
        )

        is_vet = df["top_n_avg"].notna() & df["projected_ppg"].notna()
        is_rookie = df["projected_ppg"].notna() & df["top_n_avg"].isna()
        is_history_only = df["top_n_avg"].notna() & df["projected_ppg"].isna()
        conditions = [is_vet, is_rookie, is_history_only]
        choices = [
            (df["scaled_proj"] * cfg.weight_projection)
            + (df["scaled_hist"] * cfg.weight_last_year),
            df["scaled_proj"],
            df["scaled_hist"],
        ]
        df["score"] = np.select(conditions, choices, default=0.0)

        # --- TIERED PLAYER BOOST LOGIC ---
        boost_list_path = settings.BASE_DIR / "player_boost.json"
        if boost_list_path.exists():
            boost_data = load_json(boost_list_path)
            log.info(f"Loaded tiered boost data from {boost_list_path}.")
            tiers = {
                "max": (cfg.boost_max, "max_boost_slugs"),
                "large": (cfg.boost_large, "large_boost_slugs"),
                "medium": (cfg.boost_medium, "medium_boost_slugs"),
                "small": (cfg.boost_small, "small_boost_slugs"),
            }
            for tier_name, (boost_value, json_key) in tiers.items():
                slugs_to_boost = boost_data.get(json_key, [])
                if slugs_to_boost:
                    is_boosted_player = df["slug"].isin(slugs_to_boost)
                    boost_factor = 1 + boost_value
                    df.loc[is_boosted_player, "score"] *= boost_factor
                    log.info(
                        f"Applied a {boost_value:.0%} '{tier_name}' boost to {is_boosted_player.sum()} players."
                    )
                    log.info(f"'{tier_name}' boosted players: {slugs_to_boost}")
        else:
            log.warning(
                f"player_boost.json not found at {boost_list_path}. Skipping player boost."
            )

        df["expected_ppg"] = df["score"]

        # --- NEW: PLAYER MIMIC LOGIC ---
        mimic_path = settings.BASE_DIR / "player_mimics.json"
        if mimic_path.exists():
            mimic_map = load_json(mimic_path)
            log.info(f"Found and loaded {len(mimic_map)} player mimic rules.")
            for target_slug, source_slug in mimic_map.items():

                target_rows = df["slug"] == target_slug
                source_rows = df["slug"] == source_slug

                if not target_rows.any():
                    log.warning(f"Mimic target '{target_slug}' not found. Skipping.")
                    continue
                if not source_rows.any():
                    log.warning(
                        f"Mimic source '{source_slug}' not found for target '{target_slug}'. Skipping."
                    )
                    continue

                original_ppg = df.loc[target_rows, "expected_ppg"].iloc[0]
                source_ppg = df.loc[source_rows, "expected_ppg"].iloc[0]

                df.loc[target_rows, "expected_ppg"] = source_ppg

                log.warning(
                    "Player Mimic override applied.",
                    extra={
                        "target_player": target_slug,
                        "source_player": source_slug,
                        "original_ppg": f"{original_ppg:.2f}",
                        "new_ppg": f"{source_ppg:.2f}",
                    },
                )
        # --- END OF NEW LOGIC ---

        log.info("Final 'expected_ppg' calculation complete.")

        # Final diagnostic checks remain the same
        log.info(
            f"Final check before saving. Data for Ja'Marr Chase:\n{df[df['slug'] == 'jamarr-chase'][['slug', 'top_n_avg', 'scaled_hist', 'scaled_proj', 'expected_ppg']].to_string()}"
        )
        log.info(
            f"Final check before saving. Data for Ashton Jeanty:\n{df[df['slug'] == 'ashton-jeanty'][['slug', 'top_n_avg', 'scaled_hist', 'scaled_proj', 'expected_ppg']].to_string()}"
        )
        log.info(
            f"Final check before saving. Data for Christian McCaffrey:\n{df[df['slug'] == 'christian-mccaffrey'][['slug', 'top_n_avg', 'scaled_hist', 'scaled_proj', 'expected_ppg']].to_string()}"
        )

        save_json(output_path, df.to_dict(orient="records"))
        log.info("Stats pipeline completed successfully.")
    except Exception as e:
        log.exception("Stats pipeline failed.", extra={"error": str(e)})
        raise
