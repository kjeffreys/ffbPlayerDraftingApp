# Path: ffbPlayerDraftingApp/backend/data_sources/sleeper.py

"""Data source for fetching player information from the Sleeper API."""

from typing import Any
import requests


from backend.logging_config import log  # Corrected import path
from backend.settings import settings  # Corrected import path


def fetch_all_players() -> dict[str, Any]:
    """
    Fetches the complete player list from the Sleeper API.

    Returns:
        A dictionary where keys are player IDs and values are player data objects.

    Raises:
        requests.RequestException: If the API request fails.
    """
    url = settings.SLEEPER_API_URL
    log.info("Fetching all players from Sleeper API.", extra={"url": url})

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

        players_data = response.json()

        log.info(
            "Successfully fetched player data.",
            extra={"player_count": len(players_data)},
        )
        return players_data
    except requests.RequestException:
        # log.exception automatically captures exception info
        log.exception("Sleeper API request failed.", extra={"url": url})
        raise  # Re-raise the exception to be handled by the calling pipeline
