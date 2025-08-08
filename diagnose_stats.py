# diagnose_stats.py
import pandas as pd
import datetime

# This script needs to import functions from the project
from backend.logging_config import log
from backend.settings import settings
from backend.storage.file_store import load_json
from backend.data_sources.historical import fetch_last_year_weekly_stats
from backend.utils import create_hybrid_slug_map
from backend.transforms.compute_ppg import calculate_top_n_games_avg


def run_stats_diagnosis(date_str: str):
    """
    Runs a diagnostic on the historical PPG calculation in the stats pipeline.
    """
    log.info("--- STARTING STATS PIPELINE DIAGNOSIS ---")

    # --- 1. Load Input Data ---
    input_path = settings.DATA_DIR / date_str / "players_enriched.json"
    log.info(f"Loading input file from: {input_path}")
    df = pd.DataFrame(load_json(input_path))
    cfg = settings.league_config
    log.info(
        f"Successfully loaded DataFrame. Shape: {df.shape}. Columns: {df.columns.tolist()}"
    )

    # --- 2. Fetch and Map Historical Data ---
    log.info("Fetching and mapping historical scores...")
    hist_scores = fetch_last_year_weekly_stats()
    canonical_slugs = df["slug"].dropna().unique().tolist()
    mapped_hist_scores = create_hybrid_slug_map(hist_scores, canonical_slugs)
    log.info(
        f"Historical data mapped. Found scores for {len(mapped_hist_scores)} players."
    )

    # --- 3. VERIFY INPUTS FOR KEY PLAYERS ---
    # We will spot-check players we expect to have historical data
    players_to_check = ["jamarr-chase", "justin-jefferson", "patrick-mahomes-ii"]
    log.info(f"\n--- VERIFYING INPUT DATA FOR: {players_to_check} ---")
    for slug_to_check in players_to_check:
        if slug_to_check in mapped_hist_scores:
            scores = mapped_hist_scores[slug_to_check]
            log.info(
                f"GROUND TRUTH: Found historical data for '{slug_to_check}'. Scores: {scores}"
            )
        else:
            log.warning(
                f"GROUND TRUTH: Did NOT find historical data for '{slug_to_check}' in mapped_hist_scores dict."
            )

    # --- 4. EXECUTE THE FUNCTION ---
    log.info("\n--- EXECUTING calculate_top_n_games_avg ---")
    # We pass the exact same inputs as the main script
    top_n_avg_array = calculate_top_n_games_avg(
        df["slug"], mapped_hist_scores, cfg.top_game_count
    )
    log.info(f"Function returned a NumPy array of shape: {top_n_avg_array.shape}")

    # --- 5. DIAGNOSE THE OUTPUT ---
    log.info("\n--- DIAGNOSING THE ASSIGNMENT ---")
    # Create a temporary DataFrame to inspect the alignment
    diag_df = pd.DataFrame(
        {"slug_from_df": df["slug"], "top_n_avg_from_array": top_n_avg_array}
    )

    # Check the results for our key players
    log.info(f"Checking diagnosis results for: {players_to_check}")
    print(diag_df[diag_df["slug_from_df"].isin(players_to_check)].to_string())

    # Check how many non-NaN values we got in total
    non_nan_count = diag_df["top_n_avg_from_array"].notna().sum()
    log.info(
        f"\nTotal non-NaN values in the output array: {non_nan_count} out of {len(diag_df)}"
    )

    # Assign to the main DataFrame and check again
    df["top_n_avg"] = top_n_avg_array
    log.info(
        "Assigned array to df['top_n_avg']. Checking the same key players inside the final DataFrame:"
    )
    print(df[df["slug"].isin(players_to_check)][["slug", "top_n_avg"]].to_string())


if __name__ == "__main__":
    # Use today's date or specify a date string with a real data directory
    today_str = datetime.date.today().isoformat()
    run_stats_diagnosis(date_str=today_str)
