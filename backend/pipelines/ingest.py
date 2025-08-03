# backend/backend/pipelines/ingest.py

import datetime
import requests
from data_sources.sleeper import fetch_all_players
from logging_config import setup_logging
from settings import settings
from storage.file_store import save_json

log = setup_logging(__name__)


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

    except Exception:
        # The specific exceptions are logged by the lower-level functions.
        # This top-level catch signals the entire pipeline step's failure.
        log.exception("Ingest pipeline failed.")
        # In a real-world scenario, you might want to raise this to the CLI
        # to return a non-zero exit code. For now, logging is sufficient.
