# Path: ffbPlayerDraftingApp/backend/pipelines/ingest.py

"""Pipeline for ingesting raw player data from the Sleeper API."""

import datetime
import requests  # Used implicitly by fetch_all_players, good to list for clarity

from backend.data_sources.sleeper import fetch_all_players  # Corrected import path
from backend.logging_config import log  # Corrected import path
from backend.settings import settings  # Corrected import path
from backend.storage.file_store import save_json  # Corrected import path


def run_ingest(date_str: str | None = None):
    """
    Executes the ingest pipeline:
    1. Fetches all player data from the Sleeper API.
    2. Saves the raw data to a timestamped JSON file.

    Args:
        date_str (str | None): The date in 'YYYY-MM-DD' format.
                               If None, defaults to today.
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    log.info("Starting ingest pipeline.", extra={"date": date_str})

    output_dir = settings.DATA_DIR / date_str
    output_path = output_dir / "raw_players.json"

    try:
        # 1. Fetch data from the source
        log.info("Fetching raw player data from Sleeper.")
        raw_players = fetch_all_players()

        # 2. Save the artifact for this phase
        log.info(
            "Saving raw player data as artifact.", extra={"path": str(output_path)}
        )
        save_json(output_path, raw_players)

        log.info("Ingest pipeline completed successfully.")

    except (requests.RequestException, IOError, TypeError):
        # Catch specific, expected exceptions from the data source or file operations.
        log.exception("Ingest pipeline failed.")
        raise
    except Exception:
        # Catch any other unexpected errors.
        log.exception("An unexpected error occurred in the ingest pipeline.")
        raise
