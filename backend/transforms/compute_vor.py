# Path: ffbPlayerDraftingApp/backend/transforms/compute_vor.py (DEFINITIVE FINAL)

import pandas as pd
from backend.logging_config import log
from backend.settings import settings


def calculate_vor(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Calculating Value over Replacement (VOR) with FLEX logic.")
    cfg = settings.league_config
    roster = cfg.roster

    replacement_levels = {}

    # Step 1: Calculate replacement for dedicated positions
    for pos, starters in roster.model_dump().items():
        if pos == "FLEX":
            continue
        # Sort by expected_ppg to find the Nth player
        pos_df = df[df["position"] == pos].sort_values("expected_ppg", ascending=False)
        # The replacement player is the one just after the last starter
        replacement_idx = cfg.teams * starters

        if 0 < replacement_idx <= len(pos_df):
            # .iloc[replacement_idx] would be the first bench player,
            # but standard VOR often uses the last starter as the baseline.
            # We'll stick to the standard: last starter is the line.
            replacement_levels[pos] = pos_df.iloc[replacement_idx - 1]["expected_ppg"]
        else:
            # If there aren't enough players to fill starting spots, replacement is 0
            replacement_levels[pos] = 0.0

    # Step 2: Calculate FLEX replacement level ONLY IF FLEX spots exist
    if roster.FLEX > 0:
        flex_pool = pd.concat(
            [
                df[df["position"] == "RB"].iloc[cfg.teams * roster.RB :],
                df[df["position"] == "WR"].iloc[cfg.teams * roster.WR :],
                df[df["position"] == "TE"].iloc[cfg.teams * roster.TE :],
            ]
        ).sort_values("expected_ppg", ascending=False)

        flex_replacement_idx = cfg.teams * roster.FLEX
        if 0 < flex_replacement_idx <= len(flex_pool):
            replacement_levels["FLEX"] = flex_pool.iloc[flex_replacement_idx - 1][
                "expected_ppg"
            ]
        else:
            replacement_levels["FLEX"] = 0.0
    else:
        # If FLEX = 0, explicitly set the level to 0
        replacement_levels["FLEX"] = 0.0

    log.info("Determined replacement levels (PPG).", extra=replacement_levels)

    # Step 3: Calculate VOR for each player
    def get_player_vor(row):
        pos_vor = row["expected_ppg"] - replacement_levels.get(row["position"], 0.0)

        # --- THE FINAL FIX ---
        # Only consider FLEX VOR if the league actually has FLEX spots
        if row["position"] in ["RB", "WR", "TE"] and cfg.roster.FLEX > 0:
            flex_vor = row["expected_ppg"] - replacement_levels.get("FLEX", 0.0)
            return max(pos_vor, flex_vor)

        # For QBs, Ks, DEFs, or if FLEX=0, just use the positional VOR
        return pos_vor

    df["vor"] = df.apply(get_player_vor, axis=1)
    return df
