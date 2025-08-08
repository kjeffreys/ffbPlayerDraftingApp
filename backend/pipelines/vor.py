# Path: ffbPlayerDraftingApp/backend/pipelines/vor.py (FINAL)

import datetime
import pandas as pd
import numpy as np

from backend.logging_config import log
from backend.settings import settings
from backend.storage.file_store import load_json, save_json
from backend.transforms.compute_vor import calculate_vor


def run_vor(date_str: str | None = None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    log.info("Starting VOR pipeline.", extra={"date": date_str})

    # --- FIX: Use the dynamic date_str passed in from the CLI ---
    input_path = settings.DATA_DIR / date_str / "players_with_ppg.json"
    output_path = settings.DATA_DIR / date_str / "players_final.json"
    try:
        ppg_data = load_json(input_path)
        df = pd.DataFrame(ppg_data)

        # --- NEW: Filter out players who do not have an ADP ---
        # This cleans the final output for the UI.
        initial_count = len(df)
        df.dropna(subset=["adp"], inplace=True)
        final_count = len(df)
        log.info(
            f"Filtered out players with no ADP. Removed: {initial_count - final_count}, Remaining: {final_count}"
        )

        # Continue with VOR calculation on the cleaned DataFrame
        df_with_vor = calculate_vor(df.copy())
        final_df = df_with_vor.sort_values(by="vor", ascending=False)
        final_df["rank"] = range(1, len(final_df) + 1)

        log.info("Formatting final output.")

        # This formatting logic is good. No changes needed here.
        formatted_df = pd.DataFrame()
        formatted_df["id"] = final_df["rank"]
        formatted_df["name"] = final_df["first_name"] + " " + final_df["last_name"]
        formatted_df["team"] = final_df["team"]
        formatted_df["position"] = final_df["position"]
        formatted_df["adp"] = final_df["adp"].round(1)
        formatted_df["vor"] = final_df["vor"].round(2)
        formatted_df["bye"] = final_df["bye_week"].astype("Int64")
        formatted_df["ppg"] = final_df["expected_ppg"].round(2)

        output_data = formatted_df.replace({np.nan: None}).to_dict(orient="records")
        save_json(output_path, output_data)
        log.info(
            "VOR pipeline completed. Final artifact created.",
            extra={"path": str(output_path)},
        )

    except Exception as e:
        log.exception("VOR pipeline failed.", extra={"error": str(e)})
        raise
