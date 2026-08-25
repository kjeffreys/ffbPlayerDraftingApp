# Path: ffbPlayerDraftingApp/backend/transforms/compute_vor.py (DEFINITIVE FINAL)

import pandas as pd
from backend.logging_config import log
from backend.settings import settings


def calculate_vor(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    log.info("Calculating Value over Replacement (VOR) with FLEX/SUPERFLEX logic.")
    cfg = settings.league_config
    roster = cfg.roster.model_dump()
    replacement_levels = {}
    active_slots = set()
    selected_indexes = set()
    slot_eligibility = {
        "QB": {"QB"},
        "RB": {"RB"},
        "WR": {"WR"},
        "TE": {"TE"},
        "K": {"K"},
        "DEF": {"DEF"},
        "SUPERFLEX": {"QB", "RB", "WR", "TE"},
        "FLEX": {"RB", "WR", "TE"},
    }
    slot_order = ["QB", "RB", "WR", "TE", "K", "DEF", "SUPERFLEX", "FLEX"]

    for slot in slot_order:
        starters = int(roster.get(slot, 0) or 0)
        if starters <= 0:
            replacement_levels[slot] = 0.0
            continue
        active_slots.add(slot)
        pool = df[
            df["position"].isin(slot_eligibility[slot])
            & ~df.index.isin(selected_indexes)
        ].sort_values("expected_ppg", ascending=False)
        demand = cfg.teams * starters
        chosen = pool.iloc[:demand]
        selected_indexes.update(chosen.index.tolist())
        replacement_levels[slot] = (
            chosen.iloc[-1]["expected_ppg"] if 0 < demand <= len(chosen) else 0.0
        )

    position_slots = {
        "QB": ["QB", "SUPERFLEX"],
        "RB": ["RB", "FLEX", "SUPERFLEX"],
        "WR": ["WR", "FLEX", "SUPERFLEX"],
        "TE": ["TE", "FLEX", "SUPERFLEX"],
        "K": ["K"],
        "DEF": ["DEF"],
    }

    def get_player_vor(row):
        eligible_slots = [
            slot for slot in position_slots.get(row["position"], [])
            if slot in active_slots
        ]
        replacement_floor = min(
            (replacement_levels.get(slot, 0.0) for slot in eligible_slots),
            default=0.0,
        )
        return row["expected_ppg"] - replacement_floor

    df = df.copy()
    df["vor"] = df.apply(get_player_vor, axis=1)
    return df, replacement_levels
