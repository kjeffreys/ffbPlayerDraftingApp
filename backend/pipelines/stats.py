# backend/backend/pipelines/stats.py
"""Pipeline for calculating composite player statistics like expected_ppg."""

import datetime
import pandas as pd
from data_sources.historical import fetch_last_year_weekly_stats
from logging_config import setup_logging
from models import PlayerEnriched
from settings import settings
from storage.file_store import load_json, save_json
from transforms.compute_ppg import calculate_top_n_games_avg
from transforms.normalize import calculate_z_scores

log = setup_logging(__name__)


def run_stats(date_str: str | None = None):
    """
    Executes the stats pipeline:
    1. Loads players_enriched.json.
    2. Fetches historical weekly scores.
    3. Calculates top-N game average for vets.
    4. Normalizes (z-score) the projections and historical averages.
    5. Computes a weighted 'expected_ppg' score based on league_config.
    6. Applies a rookie bonus, if applicable.
    7. Saves the result to players_with_ppg.json.
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()
    log.info("Starting stats pipeline.", extra={"date": date_str})

    data_dir = settings.DATA_DIR / date_str
    input_path = data_dir / "players_enriched.json"
    output_path = data_dir / "players_with_ppg.json"

    try:
        # 1. Load data and create a DataFrame for easy manipulation
        enriched_players_data = load_json(input_path)
        df = pd.DataFrame(enriched_players_data).set_index("player_id")

        # 2. Fetch historical data
        historical_stats = fetch_last_year_weekly_stats()

        # 3. Calculate metrics
        df["top_n_avg"] = calculate_top_n_games_avg(
            df.index.tolist(), historical_stats, settings.league_config.top_game_count
        )

        # 4. Normalize metrics into z-scores
        df["z_projection"] = calculate_z_scores(df["projected_points"])
        df["z_top_n_avg"] = calculate_z_scores(df["top_n_avg"])

        # 5. Compute weighted expected_ppg score
        cfg = settings.league_config
        df["expected_ppg"] = (
            df["z_projection"] * cfg.weight_projection
            + df["z_top_n_avg"] * cfg.weight_last_year
        )

        # 6. Apply rookie bonus
        is_rookie = df["top_n_avg"].isna()
        df.loc[is_rookie, "expected_ppg"] *= 1 + cfg.rookie_bonus

        log.info(
            "Calculated expected_ppg.",
            extra={
                "rookie_count": int(is_rookie.sum()),
                "rookie_bonus": cfg.rookie_bonus,
            },
        )

        # --- NEW STEP 6.5: Rescale the composite z-score to a PPG-like scale ---
        # We use the mean and std dev of the original projections as our target scale.
        target_mean = df["projected_points"].mean()
        target_std_dev = df["projected_points"].std()

        # Denormalize: new_value = (z_score * target_std) + target_mean
        df["expected_ppg"] = (df["expected_ppg"] * target_std_dev) + target_mean

        log.info(
            "Rescaled expected_ppg to a familiar PPG range.",
            extra={"target_mean": target_mean, "target_std_dev": target_std_dev},
        )

        # 7. Merge results back and save
        output_data = df.reset_index().to_dict(orient="records")
        save_json(output_path, output_data)

        log.info("Stats pipeline completed successfully.")

    except (OSError, KeyError) as e:
        log.exception("Stats pipeline failed.", extra={"error": str(e)})
        raise
