# backend/backend/pipelines/vor.py
"""Pipeline for calculating VOR and generating the final player list."""

import datetime
import pandas as pd
from logging_config import setup_logging
from settings import settings
from storage.file_store import load_json, save_json
from transforms.compute_vor import calculate_vor

log = setup_logging(__name__)


def run_vor(date_str: str | None = None):
    """
    Executes the VOR pipeline:
    1. Loads players_with_ppg.json.
    2. Calculates VOR for each player based on league settings.
    3. Sorts all players by VOR descending.
    4. Adds a final overall rank.
    5. Saves the final, draft-ready list to players_final.json.
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()
    log.info("Starting VOR pipeline.", extra={"date": date_str})

    data_dir = settings.DATA_DIR / date_str
    input_path = data_dir / "players_with_ppg.json"
    output_path = data_dir / "players_final.json"

    try:
        # 1. Load data from the 'stats' phase
        ppg_data = load_json(input_path)
        df = pd.DataFrame(ppg_data)

        # 2. Calculate VOR
        df_with_vor = calculate_vor(df.copy())

        # 3. Sort by VOR to create the master ranking
        final_df = df_with_vor.sort_values(by="vor", ascending=False)

        # 4. Add the final rank
        final_df["rank"] = range(1, len(final_df) + 1)

        # 5. Save the final artifact
        output_data = final_df.to_dict(orient="records")
        save_json(output_path, output_data)

        log.info(
            "VOR pipeline completed successfully. Final artifact created.",
            extra={"path": str(output_path)},
        )

    except (OSError, KeyError) as e:
        log.exception("VOR pipeline failed.", extra={"error": str(e)})
        raise
