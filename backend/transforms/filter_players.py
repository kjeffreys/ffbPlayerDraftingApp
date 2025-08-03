# backend/backend/transforms/filter_players.py
"""Functions for filtering lists of players based on rules."""


from backend.logging_config import setup_logging
from backend.models import PlayerRaw

log = setup_logging(__name__)


def keep_rostered_and_relevant(
    players: list[PlayerRaw], relevant_positions: set[str]
) -> list[PlayerRaw]:
    """
    Filters a list of players, keeping only those who are:
    1. On an NFL team (i.e., team is not None).
    2. Have a position defined in the league's roster settings.

    Args:
        players: A list of PlayerRaw models.
        relevant_positions: A set of position strings (e.g., {"QB", "RB", ...}).

    Returns:
        A filtered list of PlayerRaw models.
    """
    initial_count = len(players)
    log.info(
        "Filtering players.",
        extra={
            "initial_count": initial_count,
            "relevant_positions": list(relevant_positions),
        },
    )

    filtered_players = [
        player
        for player in players
        if player.team is not None and player.position in relevant_positions
    ]

    final_count = len(filtered_players)
    log.info(
        "Player filtering complete.",
        extra={
            "initial_count": initial_count,
            "final_count": final_count,
            "players_removed": initial_count - final_count,
        },
    )

    return filtered_players
