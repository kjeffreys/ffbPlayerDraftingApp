# Path: ffbPlayerDraftingApp/backend/transforms/compute_ppg.py

import pandas as pd
import numpy as np


def calculate_top_n_games_avg(
    slug_series: pd.Series, historical_stats: dict[str, list[float]], top_n: int
) -> np.ndarray:
    """
    Calculates the average of each player's top N weekly scores from last year.
    Returns a NumPy array to ensure direct, index-free assignment to the DataFrame.
    """
    ppg_scores = []
    for slug in slug_series:
        scores = historical_stats.get(slug)
        if scores:
            sorted_scores = sorted(scores, reverse=True)
            games_to_average = min(len(sorted_scores), top_n)
            top_scores = sorted_scores[:games_to_average]
            if games_to_average > 0:
                ppg_scores.append(sum(top_scores) / games_to_average)
            else:
                ppg_scores.append(np.nan)
        else:
            ppg_scores.append(np.nan)
    return np.array(ppg_scores)
