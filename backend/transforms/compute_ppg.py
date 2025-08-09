# Path: ffbPlayerDraftingApp/backend/transforms/compute_ppg.py (DEFINITIVE FINAL)
import pandas as pd
import numpy as np
from backend.settings import settings  # Import settings to access config


def calculate_top_n_games_avg(
    slug_series: pd.Series, historical_stats: dict[str, list[float]], top_n: int
) -> pd.Series:
    """
    For each slug, calculates the average of their top N weekly scores,
    first filtering out scores below a minimum threshold to exclude dud games.
    """
    cfg = settings.league_config
    min_score = cfg.min_historical_score

    def get_player_avg(slug):
        scores = historical_stats.get(slug)
        if not scores:
            return np.nan

        # --- THE FINAL FIX: Filter out injury-shortened "dud" games ---
        filtered_scores = [s for s in scores if s >= min_score]

        if not filtered_scores:
            return np.nan  # Player had scores, but none met the threshold

        sorted_scores = sorted(filtered_scores, reverse=True)
        games_to_average = min(len(sorted_scores), top_n)
        top_scores = sorted_scores[:games_to_average]

        if not top_scores:
            return np.nan

        return sum(top_scores) / games_to_average

    return slug_series.apply(get_player_avg)
