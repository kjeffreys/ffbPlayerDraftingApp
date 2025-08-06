# Path: ffbPlayerDraftingApp/backend/transforms/compute_vor.py

"""Function for calculating Value over Replacement (VOR)."""

import pandas as pd

from backend.logging_config import log  # Corrected import path
from backend.settings import settings  # Corrected import path


def calculate_vor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Value over Replacement (VOR) for each player.

    VOR is defined as a player's score minus the score of a "replacement-level"
    player at the same position. The replacement level is determined by the last
    expected starter based on league size and roster settings.

    Args:
        df: A DataFrame of players with 'position' and 'expected_ppg' columns.

    Returns:
        The same DataFrame with a 'vor' column added.
    """
    log.info("Calculating Value over Replacement (VOR).")

    cfg = settings.league_config
    roster_cfg = cfg.roster  # pylint: disable=no-member

    replacement_levels = {}

    # Determine the replacement level PPG for each core position
    for position, num_starters in roster_cfg.model_dump().items():
        # FLEX is handled by the value of RBs/WRs/TEs, so we skip it here.
        # Also skip positions with 0 starters.
        if position == "FLEX" or num_starters == 0:
            continue

        # Filter the DataFrame to players of the current position
        pos_df = df[df["position"] == position].sort_values(
            by="expected_ppg", ascending=False
        )

        # The replacement level is the Nth player, where N = teams * starters
        replacement_idx = cfg.teams * num_starters  # pylint: disable=no-member

        # Ensure we don't go out of bounds if there are fewer players than starters
        if replacement_idx > 0 and replacement_idx <= len(pos_df):
            # The replacement player is at index N-1 (since it's 0-indexed)
            replacement_player_ppg = pos_df.iloc[replacement_idx - 1]["expected_ppg"]
            replacement_levels[position] = replacement_player_ppg
        else:
            # If not enough players, the replacement value is effectively zero.
            replacement_levels[position] = 0.0
            log.warning(
                "Not enough players to determine replacement level for position.",
                extra={
                    "position": position,
                    "needed_players": replacement_idx,
                    "available_players": len(pos_df),
                },
            )

    log.info("Determined replacement levels (PPG).", extra=replacement_levels)

    # Calculate VOR for each player by subtracting their position's replacement PPG.
    # If a player's position has no defined replacement level, their VOR is 0.
    df["vor"] = df.apply(
        lambda row: row["expected_ppg"] - replacement_levels.get(row["position"], 0.0),
        axis=1,
    )

    return df
