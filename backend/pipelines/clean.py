# Path: ffbPlayerDraftingApp/backend/pipelines/clean.py

"""Pipeline for cleaning raw player data based on league configuration."""

import datetime

from pydantic import ValidationError

from backend.logging_config import log  # Corrected import path
from backend.models import PlayerRaw  # Corrected import path
from backend.settings import settings  # Corrected import path
from backend.storage.file_store import load_json, save_json  # Corrected import path
from backend.transforms.filter_players import (
    keep_rostered_and_relevant,
)  # Corrected import path


def run_clean(date_str: str | None = None):
    """
    Executes the clean pipeline:
    1. Loads raw_players.json artifact.
    2. Validates and parses data into PlayerRaw models.
    3. Filters out players who are not on a team or have irrelevant positions
       based on the league_config.json settings.
    4. Saves the cleaned data to roster_players.json.

    Args:
        date_str (str | None): The date in 'YYYY-MM-DD' format.
                               If None, defaults to today.
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    log.info("Starting clean pipeline.", extra={"date": date_str})

    data_dir = settings.DATA_DIR / date_str
    input_path = data_dir / "raw_players.json"
    output_path = data_dir / "roster_players.json"

    try:
        # 1. Load the artifact from the previous phase
        raw_players_dict = load_json(input_path)
        if not raw_players_dict:
            log.warning(
                "Input file is empty, skipping.", extra={"path": str(input_path)}
            )
            return

        # 2. Validate data with Pydantic models.
        # The raw data is a dict of dicts; we want a list of models.
        players_to_process = [PlayerRaw(**p) for p in raw_players_dict.values()]

        # 3. Dynamically get relevant positions from the loaded league config.
        # We exclude "FLEX" as it's a roster spot, not a player position.
        roster_settings = (
            settings.league_config.roster.model_dump()  # pylint: disable=no-member
        )  # pylint: disable=no-member
        relevant_positions = {pos for pos in roster_settings if pos != "FLEX"}

        # 4. Apply the transformation
        rostered_players = keep_rostered_and_relevant(
            players_to_process, relevant_positions
        )

        # 5. Save the new artifact
        # Convert Pydantic models back to dicts for JSON serialization
        output_data = [player.model_dump(by_alias=True) for player in rostered_players]
        save_json(output_path, output_data)

        log.info("Clean pipeline completed successfully.")

    except (IOError, ValidationError) as e:
        log.exception("Clean pipeline failed.", extra={"error": str(e)})
        raise
    except Exception:
        log.exception("An unexpected error occurred in the clean pipeline.")
        raise
