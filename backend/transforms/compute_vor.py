# backend/backend/transforms/compute_vor.py
"""Function for calculating Value over Replacement (VOR)."""

import pandas as pd

from backend.logging_config import setup_logging
from backend.settings import settings

log = setup_logging(__name__)


def calculate_vor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Value over Replacement (VOR) for each player.

    Args:
        df: A DataFrame of players with 'position' and 'expected_ppg' columns.

    Returns:
        The same DataFrame with a 'vor' column added.
    """
    log.info("Calculating Value over Replacement (VOR).")

    cfg = settings.league_config
    roster_cfg = cfg.roster

    replacement_levels = {}

    # Determine the replacement level PPG for each core position
    for position, num_starters in roster_cfg.model_dump().items():
        if position == "FLEX" or num_starters == 0:
            continue

        # Find players for the current position
        pos_df = df[df["position"] == position].sort_values(
            by="expected_ppg", ascending=False
        )

        # Replacement level is the Nth player, where N = teams * starters
        replacement_idx = cfg.teams * num_starters

        # Ensure we don't go out of bounds
        if replacement_idx > 0 and replacement_idx <= len(pos_df):
            # The replacement player is at index N-1
            replacement_player_ppg = pos_df.iloc[replacement_idx - 1]["expected_ppg"]
            replacement_levels[position] = replacement_player_ppg
        else:
            # If not enough players, replacement value is 0 or a low floor
            replacement_levels[position] = 0.0
            log.warning(
                "Not enough players to determine replacement level for position.",
                extra={
                    "position": position,
                    "needed": replacement_idx,
                    "available": len(pos_df),
                },
            )

    log.info("Determined replacement levels.", extra=replacement_levels)

    # Calculate VOR for each player based on their position's replacement level
    df["vor"] = df.apply(
        lambda row: row["expected_ppg"] - replacement_levels.get(row["position"], 0.0),
        axis=1,
    )

    return df
