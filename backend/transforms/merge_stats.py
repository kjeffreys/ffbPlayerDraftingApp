# backend/backend/transforms/merge_stats.py
"""Functions for merging external stats with player data."""


from backend.logging_config import setup_logging
from backend.models import PlayerEnriched, PlayerRaw
from backend.utils import slugify

log = setup_logging(__name__)


def merge_external_data(
    players: list[PlayerRaw],
    adp_map: dict[str, float],
    projections_map: dict[str, float],
) -> list[PlayerEnriched]:
    """
    Merges player data with external stats (ADP, projections).

    Args:
        players: The list of cleaned PlayerRaw objects.
        adp_map: A dict mapping player name slugs to ADP.
        projections_map: A dict mapping player name slugs to projected points.

    Returns:
        A new list of PlayerEnriched objects.
    """
    enriched_players = []
    adp_matches = 0
    proj_matches = 0

    for player in players:
        # Create a consistent key for lookups
        player_slug = slugify(f"{player.first_name} {player.last_name}")

        adp = adp_map.get(player_slug)
        if adp is not None:
            adp_matches += 1

        projection = projections_map.get(player_slug)
        if projection is not None:
            proj_matches += 1

        enriched_player = PlayerEnriched(
            **player.model_dump(),  # Inherit all fields from the base player
            adp=adp,
            projected_points=projection,
        )
        enriched_players.append(enriched_player)

    log.info(
        "External data merge complete.",
        extra={
            "total_players": len(players),
            "adp_matches": adp_matches,
            "projection_matches": proj_matches,
        },
    )
    return enriched_players
