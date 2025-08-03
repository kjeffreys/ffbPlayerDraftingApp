# backend/backend/transforms/compute_ppg.py
"""Functions for computing various forms of points-per-game (PPG)."""


import pandas as pd


def calculate_top_n_games_avg(
    player_ids: list[str], historical_stats: dict[str, list[float]], top_n: int
) -> pd.Series:
    """
    Calculates the average of each player's top N weekly scores from last year.

    Args:
        player_ids: The list of player IDs to process.
        historical_stats: A dict mapping player_id to their weekly scores.
        top_n: The number of top games to consider (e.g., 6).

    Returns:
        A pandas Series indexed by player_id with their top-N-game-avg PPG.
        Rookies or players with no data will be missing (NaN).
    """
    ppg_data = {}
    for player_id in player_ids:
        scores = historical_stats.get(player_id)
        if scores and len(scores) >= top_n:
            top_scores = sorted(scores, reverse=True)[:top_n]
            ppg_data[player_id] = sum(top_scores) / top_n

    return pd.Series(ppg_data, name="top_n_avg").reindex(player_ids)
