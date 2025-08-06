# Path: ffbPlayerDraftingApp/backend/transforms/normalize.py

"""Functions for normalizing and scaling data using z-scores."""

import pandas as pd


def calculate_z_scores(series: pd.Series) -> pd.Series:
    """
    Calculates the z-score for each value in a pandas Series.
    Z-score = (value - mean) / std_dev.

    Missing values (NaN), such as for rookies with no historical data, will be
    filled with 0. This correctly treats them as "average" in that category,
    neither penalizing nor artificially boosting them.

    Args:
        series: A pandas Series of numerical data (e.g., all player projections).

    Returns:
        A pandas Series of the same shape containing z-scores.
    """
    mean = series.mean()
    std_dev = series.std()

    # Avoid division by zero if all values in the series are identical.
    if std_dev == 0:
        return pd.Series(0.0, index=series.index)

    z_scores = (series - mean) / std_dev

    # Fill any missing values with 0, representing the mean (average).
    return z_scores.fillna(0.0)
