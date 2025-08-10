# Path: ffbPlayerDraftingApp/backend/pipelines/vor.py (DEFINITIVE FINAL)

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

    input_path = settings.DATA_DIR / date_str / "players_with_ppg.json"
    output_path = settings.DATA_DIR / date_str / "players_final.json"
    try:
        ppg_data = load_json(input_path)
        df = pd.DataFrame(ppg_data)
        cfg = settings.league_config

        # --- THE FINAL FIX: Re-ordering the VOR Logic ---

        # Step 1: Calculate replacement levels using the ORIGINAL, un-penalized scores.
        # We pass the clean DataFrame to the calculation function first.
        df_with_vor, replacement_levels = calculate_vor(df.copy())
        log.info(
            "Determined replacement levels from original scores.",
            extra=replacement_levels,
        )

        # Step 2: NOW, apply the strategic positional penalties.
        log.info("Applying positional penalties to expected_ppg.")
        if hasattr(cfg, "positional_penalties"):
            penalties = cfg.positional_penalties
            for position, penalty in penalties.items():
                if penalty < 1.0:
                    # Apply the penalty to the original ppg AND the calculated vor
                    df_with_vor.loc[
                        df_with_vor["position"] == position, "expected_ppg"
                    ] *= penalty
                    df_with_vor.loc[
                        df_with_vor["position"] == position, "vor"
                    ] *= penalty
                    log.info(f"Applied a x{penalty} penalty to {position} position.")

        # Step 3: Filter out players with no ADP (after all calculations are done).
        initial_count = len(df_with_vor)
        df_with_vor.dropna(subset=["adp"], inplace=True)
        final_count = len(df_with_vor)
        log.info(
            f"Filtered out players with no ADP. Removed: {initial_count - final_count}, Remaining: {final_count}"
        )

        # Step 4: Sort and Rank based on the final, adjusted VOR.
        final_df = df_with_vor.sort_values(by="vor", ascending=False)
        final_df["rank"] = range(1, len(final_df) + 1)

        log.info("Formatting final output.")

        # Formatting logic remains the same
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
