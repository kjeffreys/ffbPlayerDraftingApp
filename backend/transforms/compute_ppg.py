# Path: ffbPlayerDraftingApp/backend/transforms/compute_ppg.py (FINAL, CORRECTED)
import pandas as pd
import numpy as np


def calculate_top_n_games_avg(
    slug_series: pd.Series, historical_stats: dict[str, list[float]], top_n: int
) -> pd.Series:
    """
    For each slug in the series, calculates the average of their top N weekly scores.
    Returns a pandas Series with the original index, ensuring correct alignment.
    """

    def get_player_avg(slug):
        scores = historical_stats.get(slug)
        if not scores:
            return np.nan  # Explicitly return NaN for players not found

        sorted_scores = sorted(scores, reverse=True)
        games_to_average = min(len(sorted_scores), top_n)
        top_scores = sorted_scores[:games_to_average]

        # Handle case where player has scores but they are all zero
        if not top_scores or sum(top_scores) == 0:
            return np.nan

        return sum(top_scores) / games_to_average

    # .apply() preserves the index of slug_series, solving all alignment issues.
    return slug_series.apply(get_player_avg)
