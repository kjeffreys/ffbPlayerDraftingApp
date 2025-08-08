# diagnose_transform.py
import pandas as pd
import datetime

from backend.logging_config import log
from backend.settings import settings
from backend.storage.file_store import load_json
from backend.data_sources.historical import fetch_last_year_weekly_stats
from backend.utils import create_hybrid_slug_map
from backend.transforms.compute_ppg import calculate_top_n_games_avg
from backend.transforms.normalize import calculate_z_scores


def run_transform_diagnosis(date_str: str):
    log.info("--- STARTING TRANSFORM DIAGNOSIS ---")

    # --- 1. Load Data and Calculate Prereqs ---
    input_path = settings.DATA_DIR / date_str / "players_enriched.json"
    df = pd.DataFrame(load_json(input_path))
    cfg = settings.league_config

    hist_scores = fetch_last_year_weekly_stats()
    mapped_hist_scores = create_hybrid_slug_map(
        hist_scores, df["slug"].dropna().unique().tolist()
    )

    # We know this part works.
    df["top_n_avg"] = calculate_top_n_games_avg(
        df["slug"], mapped_hist_scores, cfg.top_game_count
    )

    # --- 2. TAKE "BEFORE" SNAPSHOT ---
    player_to_check = "jamarr-chase"
    log.info(f"--- TAKING 'BEFORE' SNAPSHOT for '{player_to_check}' ---")
    before_snapshot = df[df["slug"] == player_to_check][
        ["slug", "position", "top_n_avg"]
    ]
    print("BEFORE calculate_z_scores is called:")
    print(before_snapshot.to_string())

    # --- 3. EXECUTE THE PROBLEMATIC LINE ---
    log.info("\n--- EXECUTING the calculate_z_scores line... ---")
    df["z_hist"] = calculate_z_scores(df, "top_n_avg")
    log.info("Line executed.")

    # --- 4. TAKE "AFTER" SNAPSHOT ---
    log.info(f"\n--- TAKING 'AFTER' SNAPSHOT for '{player_to_check}' ---")
    after_snapshot = df[df["slug"] == player_to_check][
        ["slug", "position", "top_n_avg", "z_hist"]
    ]
    print("AFTER calculate_z_scores is called:")
    print(after_snapshot.to_string())

    # --- 5. FINAL VERDICT ---
    final_value = after_snapshot["top_n_avg"].iloc[0]
    if pd.isna(final_value):
        log.error(
            "\n*** VERDICT: The 'top_n_avg' column was destroyed by the z-score calculation! ***"
        )
    else:
        log.info(
            f"\n*** VERDICT: The 'top_n_avg' column survived. Final value: {final_value} ***"
        )


if __name__ == "__main__":
    today_str = datetime.date.today().isoformat()
    run_transform_diagnosis(date_str=today_str)
