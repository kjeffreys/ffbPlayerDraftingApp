# backend/backend/pipelines/enrich.py
"""Pipeline for enriching player data with ADP and projections."""

import datetime
from pydantic import ValidationError
import requests
from data_sources import fantasypros, yahoo
from logging_config import setup_logging
from models import PlayerRaw
from settings import settings
from storage.file_store import load_json, save_json
from transforms.merge_stats import merge_external_data

log = setup_logging(__name__)


def run_enrich(date_str: str | None = None):
    """
    Executes the enrich pipeline:
    1. Loads roster_players.json.
    2. Fetches ADP and projected points from external sources.
    3. Merges the data into an enriched player list.
    4. Saves the result to players_enriched.json.

    Args:
        date_str (str | None): The date in 'YYYY-MM-DD' format. If None, defaults to today.
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    log.info("Starting enrich pipeline.", extra={"date": date_str})

    data_dir = settings.DATA_DIR / date_str
    input_path = data_dir / "roster_players.json"
    output_path = data_dir / "players_enriched.json"

    try:
        # 1. Load data from the 'clean' phase
        cleaned_players_data = load_json(input_path)
        players = [PlayerRaw(**p) for p in cleaned_players_data]

        # 2. Fetch data from external sources
        log.info("Fetching external data sources.")
        adp_map = fantasypros.fetch_adp()
        projections_map = yahoo.fetch_projected_points()  # Using the stub

        # 3. Apply the transformation
        enriched_players = merge_external_data(players, adp_map, projections_map)

        # 4. Save the new artifact
        output_data = [p.model_dump() for p in enriched_players]
        save_json(output_path, output_data)

        log.info("Enrich pipeline completed successfully.")

    except (OSError, ValidationError, requests.RequestException, ValueError) as e:
        log.exception("Enrich pipeline failed.", extra={"error": str(e)})
        raise
    except Exception:
        log.exception("An unexpected error occurred in the enrich pipeline.")
        raise
