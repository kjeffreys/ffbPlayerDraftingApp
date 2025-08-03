# backend/backend/pipelines/clean.py
"""Pipeline for cleaning raw player data."""

import datetime
from pydantic import ValidationError
from logging_config import setup_logging
from models import PlayerRaw
from settings import settings
from storage.file_store import load_json, save_json
from transforms.filter_players import keep_rostered_and_relevant


log = setup_logging(__name__)


def run_clean(date_str: str | None = None):
    """
    Executes the clean pipeline based on league_config.json settings.
    ...
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    log.info("Starting clean pipeline.", extra={"date": date_str})

    data_dir = settings.DATA_DIR / date_str
    input_path = data_dir / "raw_players.json"
    output_path = data_dir / "roster_players.json"

    try:
        raw_players_dict = load_json(input_path)
        if not raw_players_dict:
            log.warning(
                "Input file is empty, skipping.", extra={"path": str(input_path)}
            )
            return

        players_to_process = [PlayerRaw(**p) for p in raw_players_dict.values()]

        # --- MODIFIED LOGIC ---
        # Get relevant positions directly from the loaded league config.
        # We exclude "FLEX" as it's a roster spot, not a player position.
        roster_settings = settings.league_config.roster.model_dump()
        relevant_positions = {pos for pos in roster_settings if pos != "FLEX"}

        rostered_players = keep_rostered_and_relevant(
            players_to_process, relevant_positions
        )

        output_data = [player.model_dump() for player in rostered_players]
        save_json(output_path, output_data)

        log.info("Clean pipeline completed successfully.")

    except (OSError, ValidationError) as e:
        log.exception("Clean pipeline failed.", extra={"error": str(e)})
        raise
    except Exception:
        log.exception("An unexpected error occurred in the clean pipeline.")
        raise
