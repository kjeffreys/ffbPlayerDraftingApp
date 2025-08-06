# Path: ffbPlayerDraftingApp/backend/pipelines/stats.py

import datetime, pandas as pd
from thefuzz import process
from backend.data_sources.historical import fetch_last_year_weekly_stats
from backend.logging_config import log
from backend.settings import settings
from backend.storage.file_store import load_json, save_json
from backend.transforms.compute_ppg import calculate_top_n_games_avg
from backend.transforms.normalize import calculate_z_scores


def run_stats(date_str: str | None = None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    log.info("Starting stats pipeline.", extra={"date": date_str})

    input_path = settings.DATA_DIR / date_str / "players_enriched.json"
    output_path = settings.DATA_DIR / date_str / "players_with_ppg.json"
    try:
        df = pd.DataFrame(load_json(input_path))

        hist_scores = fetch_last_year_weekly_stats()

        # --- ROBUST FUZZY MATCHING ---
        canonical_slugs = df["slug"].dropna().unique().tolist()

        def create_fuzzy_map(data_map, choices):
            return {
                match[0]: data_map[slug]
                for slug, match in {
                    slug: process.extractOne(slug, choices, score_cutoff=85)
                    for slug in data_map.keys()
                }.items()
                if match
            }

        mapped_hist_scores = create_fuzzy_map(hist_scores, canonical_slugs)

        cfg = settings.league_config
        df["top_n_avg"] = calculate_top_n_games_avg(
            df["slug"], mapped_hist_scores, cfg.top_game_count
        )

        # --- CALCULATIONS ---
        df["projected_ppg"] = df["projected_points"] / cfg.games_divisor
        df["z_proj"] = calculate_z_scores(df["projected_ppg"])
        df["z_hist"] = calculate_z_scores(df["top_n_avg"])
        df["score"] = (df["z_proj"].fillna(0) * cfg.weight_projection) + (
            df["z_hist"].fillna(0) * cfg.weight_last_year
        )
        is_rookie = df["top_n_avg"].isna()
        df.loc[is_rookie, "score"] *= 1 + cfg.rookie_bonus
        df["expected_ppg"] = (df["score"] * df["projected_ppg"].std()) + df[
            "projected_ppg"
        ].mean()

        save_json(output_path, df.to_dict(orient="records"))
        log.info("Stats pipeline completed successfully.")
    except Exception as e:
        log.exception("Stats pipeline failed.", extra={"error": str(e)})
        raise
