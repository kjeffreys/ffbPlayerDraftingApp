# backend/backend/transforms/normalize.py
"""Functions for normalizing and scaling data."""

import pandas as pd


def calculate_z_scores(series: pd.Series) -> pd.Series:
    """
    Calculates the z-score for each value in a pandas Series.
    Z-score = (value - mean) / std_dev.
    Missing values (NaN) will be filled with 0, representing the mean.

    Args:
        series: A pandas Series of numerical data.

    Returns:
        A pandas Series of z-scores.
    """
    mean = series.mean()
    std_dev = series.std()
    if std_dev == 0:  # Avoid division by zero if all values are the same
        return pd.Series(0.0, index=series.index)

    z_scores = (series - mean) / std_dev
    return z_scores.fillna(0)  # IMPORTANT: Treat missing data as average (z-score=0)
