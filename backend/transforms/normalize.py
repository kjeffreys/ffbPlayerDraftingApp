# Path: ffbPlayerDraftingApp/backend/transforms/normalize.py

"""Functions for normalizing and scaling data using z-scores."""

import pandas as pd


def calculate_z_scores(df: pd.DataFrame, column_name: str) -> pd.Series:
    """
    Calculates the z-score for each value in a column, grouped by position.
    Z-score = (value - group_mean) / group_std_dev.

    This is critical for comparing players against their peers (e.g., a WR's
    historical performance against other WRs, not against QBs).

    Args:
        df: The main player DataFrame. Must contain 'position' and the target column.
        column_name: The name of the column to calculate z-scores for (e.g., 'top_n_avg').

    Returns:
        A pandas Series containing the positionally-normalized z-scores.
    """
    # Use transform to apply the z-score calculation within each position group.
    # The lambda function calculates the z-score for its subset (the series for one position).
    z_scores = df.groupby("position")[column_name].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0.0
    )

    # Fill any remaining NaNs (for players in groups with no data) with 0.
    return z_scores.fillna(0.0)
