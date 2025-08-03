# backend/backend/data_sources/historical.py
"""Data source for fetching historical, game-by-game player stats."""


from typing import Dict, List
from logging_config import setup_logging

log = setup_logging(__name__)


def fetch_last_year_weekly_stats() -> dict[str, list[float]]:
    """
    Fetches the 2024 weekly fantasy scores for all players.

    NOTE: This is a stub using mocked data. A real implementation would hit an API
    or a data warehouse containing historical stats.

    Returns:
        A dictionary mapping player_id to a list of their weekly scores.
        e.g., {"1234": [15.2, 22.1, 8.5, ...], "5678": [10.1, 5.2, ...]}
    """
    log.warning(
        "Historical weekly stats fetching is not implemented. Returning mocked data."
    )
    # MOCK DATA: In a real system, this would be from a database or another API.
    return {
        "4017": [
            25.5,
            30.1,
            18.2,
            22.0,
            40.1,
            15.5,
            19.8,
            28.3,
            12.1,
            25.0,
            33.0,
            14.2,
        ],  # Mock C. McCaffrey
        "4875": [
            15.1,
            12.5,
            28.4,
            35.5,
            16.8,
            22.1,
            19.9,
            14.3,
            10.2,
            26.7,
        ],  # Mock CeeDee Lamb
        "6794": [
            22.0,
            25.0,
            18.0,
            21.0,
            16.0,
            19.0,
            30.0,
            15.0,
            11.0,
        ],  # Mock Patrick Mahomes
        "9423": [10.1, 12.4, 8.8, 15.1, 9.5, 11.2],  # Mock mid-tier player
    }
