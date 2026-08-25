"""Refresh draft-ready JSON files from current free data sources."""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
import pandas as pd
import requests

from backend.data_sources.historical import fetch_last_year_weekly_stats
from backend.settings import LeagueConfig
from backend.storage.file_store import save_json
from backend.utils import create_hybrid_slug_map_with_audit, slugify


ESPN_PLAYERS_URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026/"
    "segments/0/leaguedefaults/3?view=kona_player_info"
)
DYNASTYPROCESS_RANKINGS_URL = (
    "https://raw.githubusercontent.com/dynastyprocess/data/master/files/"
    "db_fpecr_latest.csv"
)

ESPN_POSITION_MAP = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DEF"}
ESPN_TEAM_MAP = {
    1: "ATL",
    2: "BUF",
    3: "CHI",
    4: "CIN",
    5: "CLE",
    6: "DAL",
    7: "DEN",
    8: "DET",
    9: "GB",
    10: "TEN",
    11: "IND",
    12: "KC",
    13: "LV",
    14: "LAR",
    15: "MIA",
    16: "MIN",
    17: "NE",
    18: "NO",
    19: "NYG",
    20: "NYJ",
    21: "PHI",
    22: "ARI",
    23: "PIT",
    24: "LAC",
    25: "SF",
    26: "SEA",
    27: "TB",
    28: "WAS",
    29: "CAR",
    30: "JAX",
    33: "BAL",
    34: "HOU",
}


@dataclass
class LeagueTarget:
    profile_id: str
    label: str
    config_path: Path
    public_file: str


LEAGUE_TARGETS = [
    LeagueTarget("default", "Default / Current", Path("backend/league_config.json"), "players.json"),
    LeagueTarget("vany", "VANY", Path("backend/league_config_vany.json"), "vany.json"),
    LeagueTarget("passion", "Passion", Path("backend/league_config_passion.json"), "passion.json"),
    LeagueTarget("guillotine", "Guillotine", Path("backend/league_config_guillotine.json"), "guillotine.json"),
    LeagueTarget("champions", "Champions", Path("backend/league_config_champions.json"), "champions.json"),
]


def _finite_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _espn_filter() -> str:
    payload = {
        "players": {
            "limit": 5000,
            "offset": 0,
            "sortDraftRanks": {
                "sortPriority": 100,
                "sortAsc": True,
                "value": "PPR",
            },
            "filterRanksForRankTypes": {"value": ["PPR", "STANDARD"]},
            "filterStatsForTopScoringPeriodIds": {
                "value": 2,
                "additionalValue": ["102026", "002025", "102025"],
            },
        }
    }
    return json.dumps(payload)


def _stat_value(player: dict[str, Any], stat_id: str, field: str) -> float | None:
    for stat in player.get("stats", []):
        if stat.get("id") == stat_id:
            return _finite_float(stat.get(field))
    return None


def fetch_espn_players() -> pd.DataFrame:
    response = requests.get(
        ESPN_PLAYERS_URL,
        headers={"x-fantasy-filter": _espn_filter(), "User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    rows = []
    for item in response.json().get("players", []):
        player = item.get("player", {})
        position = ESPN_POSITION_MAP.get(player.get("defaultPositionId"))
        if not position:
            continue
        name = str(player.get("fullName") or "").strip()
        if not name:
            continue
        ranks = player.get("draftRanksByRankType", {})
        ppr_rank = _finite_float((ranks.get("PPR") or {}).get("rank"))
        standard_rank = _finite_float((ranks.get("STANDARD") or {}).get("rank"))
        adp = _finite_float((player.get("ownership") or {}).get("averageDraftPosition"))
        projected_total = _stat_value(player, "102026", "appliedTotal")
        projected_average = _stat_value(player, "102026", "appliedAverage")
        actual_2025_average = _stat_value(player, "002025", "appliedAverage")
        rows.append(
            {
                "name": name,
                "slug": slugify(name),
                "first_name": str(player.get("firstName") or name.split()[0]),
                "last_name": str(player.get("lastName") or name.split()[-1]),
                "team": ESPN_TEAM_MAP.get(player.get("proTeamId"), ""),
                "position": position,
                "adp": adp if adp and adp > 0 else ppr_rank,
                "espn_rank": ppr_rank or standard_rank,
                "projected_points": projected_total,
                "projected_ppg_espn": projected_average,
                "actual_2025_ppg_espn": actual_2025_average,
                "injured": bool(player.get("injured")),
                "injury_status": player.get("injuryStatus"),
                "active": bool(player.get("active", True)),
            }
        )
    return pd.DataFrame(rows)


def fetch_dynastyprocess_rankings() -> pd.DataFrame:
    return pd.read_csv(DYNASTYPROCESS_RANKINGS_URL)


def _parse_bye_maps(rankings: pd.DataFrame) -> tuple[dict[str, int], dict[str, int]]:
    player_byes: dict[str, int] = {}
    team_byes: dict[str, int] = {}
    for _, row in rankings.iterrows():
        bye = _finite_float(row.get("bye"))
        if bye is None:
            continue
        bye_int = int(bye)
        player = str(row.get("player") or "")
        team = str(row.get("team") or row.get("tm") or "")
        if player:
            player_byes.setdefault(slugify(player), bye_int)
        if team:
            team_byes.setdefault(team, bye_int)
    return player_byes, team_byes



def _parse_player_team_map(rankings: pd.DataFrame) -> dict[str, str]:
    player_teams: dict[str, str] = {}
    for _, row in rankings.iterrows():
        player = str(row.get("player") or "")
        team = str(row.get("team") or row.get("tm") or "")
        if player and team and team.lower() != "nan":
            player_teams.setdefault(slugify(player), team)
    return player_teams

def _parse_ranking_maps(rankings: pd.DataFrame) -> dict[str, dict[str, float]]:
    maps: dict[str, dict[str, float]] = {"redraft": {}, "superflex": {}, "dynasty": {}}
    selections = {
        "redraft": rankings[rankings["page_type"] == "redraft-overall"],
        "superflex": rankings[rankings["page_type"] == "redraft-op"],
        "dynasty": rankings[rankings["page_type"] == "dynasty-overall"],
    }
    for key, frame in selections.items():
        for _, row in frame.iterrows():
            ecr = _finite_float(row.get("ecr"))
            player = str(row.get("player") or "")
            if player and ecr:
                maps[key][slugify(player)] = ecr
    return maps


def _top_n_average(scores: list[float], n: int) -> float | None:
    if not scores:
        return None
    return float(mean(sorted(scores, reverse=True)[:n]))


def _lower_quartile(scores: list[float]) -> float | None:
    if not scores:
        return None
    return float(np.percentile(scores, 25))


def _z_scores(series: pd.Series) -> pd.Series:
    std = series.std(skipna=True)
    if not std or math.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean(skipna=True)) / std


def _scale_positive(series: pd.Series) -> pd.Series:
    max_value = series.max(skipna=True)
    if not max_value or math.isnan(max_value) or max_value <= 0:
        return pd.Series(0.0, index=series.index)
    return series * (25.0 / max_value)




def _scale_inverse_rank(series: pd.Series) -> pd.Series:
    ranks = pd.to_numeric(series, errors="coerce")
    scores = 25.0 * np.exp(-np.maximum(ranks - 1.0, 0.0) / 80.0)
    return pd.Series(scores, index=series.index).where(ranks.notna())

def _load_config(path: Path) -> LeagueConfig:
    with open(path, "r", encoding="utf-8") as f:
        return LeagueConfig(**json.load(f))



def _json_ready(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def save_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()})
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _json_ready(row.get(key)) for key in fieldnames})


def _flatten_match_audit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened = []
    for row in rows:
        alternatives = row.get("alternatives") or []
        flattened.append(
            {
                "canonical_slug": row.get("canonical_slug", ""),
                "matched_source_slug": row.get("matched_source_slug", ""),
                "match_type": row.get("match_type", ""),
                "score": row.get("score"),
                "needs_review": row.get("needs_review", False),
                "review_reason": row.get("review_reason", ""),
                "alternatives": "; ".join(
                    f"{alt.get('source_slug')}:{alt.get('score')}" for alt in alternatives
                ),
            }
        )
    return flattened



def _build_history_review_rows(
    flattened_rows: list[dict[str, Any]], base: pd.DataFrame
) -> list[dict[str, Any]]:
    impact_rows = {
        str(row["slug"]): row
        for _, row in base.iterrows()
        if _finite_float(row.get("adp")) is not None and float(row.get("adp")) <= 120
    }
    review_rows = []
    for row in flattened_rows:
        canonical_slug = str(row.get("canonical_slug") or "")
        impact = impact_rows.get(canonical_slug)
        low_confidence_fuzzy = row.get("match_type") == "fuzzy" and row.get("needs_review")
        high_adp_missing_history = row.get("match_type") == "unmatched_canonical" and impact is not None
        if not low_confidence_fuzzy and not high_adp_missing_history:
            continue
        review_row = dict(row)
        if impact is not None:
            review_row.update(
                {
                    "name": impact.get("name"),
                    "team": impact.get("team"),
                    "position": impact.get("position"),
                    "adp": _json_ready(impact.get("adp")),
                    "espn_rank": _json_ready(impact.get("espn_rank")),
                }
            )
        review_row["review_scope"] = (
            "low_confidence_fuzzy" if low_confidence_fuzzy else "top120_missing_history"
        )
        review_rows.append(review_row)
    return sorted(
        review_rows,
        key=lambda row: (
            0 if row.get("review_scope") == "low_confidence_fuzzy" else 1,
            _finite_float(row.get("adp")) or 9999,
            str(row.get("canonical_slug") or ""),
        ),
    )

def _audit_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    for row in rows:
        match_type = str(row.get("match_type") or "unknown")
        by_type[match_type] = by_type.get(match_type, 0) + 1
    return {
        "totalRows": len(rows),
        "byType": by_type,
        "needsReview": sum(1 for row in rows if row.get("needs_review")),
    }


def _validate_final_rows(rows: list[dict[str, Any]], league_id: str) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    required = ["id", "name", "team", "position", "adp", "vor", "bye", "ppg"]
    if len(rows) < 300:
        issues.append(f"{league_id}: expected at least 300 draftable rows, found {len(rows)}.")

    seen_players: set[tuple[str, str, str]] = set()
    reported_id_issue = False
    for index, row in enumerate(rows, start=1):
        if row.get("id") != index and not reported_id_issue:
            issues.append(f"{league_id}: non-sequential id at row {index}.")
            reported_id_issue = True
        missing = [key for key in required if row.get(key) in (None, "")]
        if missing:
            issues.append(f"{league_id}: {row.get('name', '<unknown>')} missing {', '.join(missing)}.")
        if row.get("bye", 0) <= 0:
            issues.append(f"{league_id}: {row.get('name', '<unknown>')} missing bye week.")
        if row.get("adp", 999) <= 0 or row.get("adp", 999) > 360:
            warnings.append(f"{league_id}: {row.get('name', '<unknown>')} has unusual ADP {row.get('adp')}.")
        player_key = (str(row.get("name")), str(row.get("team")), str(row.get("position")))
        if player_key in seen_players:
            issues.append(f"{league_id}: duplicate player row {player_key}.")
        seen_players.add(player_key)

    top50 = rows[:50]
    top50_positions: dict[str, int] = {}
    for row in top50:
        position = str(row.get("position") or "")
        top50_positions[position] = top50_positions.get(position, 0) + 1
    if top50_positions.get("RB", 0) + top50_positions.get("WR", 0) < 20:
        warnings.append(f"{league_id}: top 50 has unusually few RB/WR players.")

    return {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "rowCount": len(rows),
        "top50Positions": top50_positions,
    }


def _top_player_audit_rows(df: pd.DataFrame, rows: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    by_name = {str(row["name"]): row for _, row in df.iterrows()}
    audit_rows = []
    for row in rows[:limit]:
        source_row = by_name.get(row["name"])
        audit_rows.append(
            {
                "rank": row["id"],
                "name": row["name"],
                "team": row["team"],
                "position": row["position"],
                "adp": row["adp"],
                "vor": row["vor"],
                "ppg": row["ppg"],
                "bye": row["bye"],
                "espn_rank": _json_ready(source_row.get("espn_rank")) if source_row is not None else None,
                "redraft_ecr": _json_ready(source_row.get("redraft_ecr")) if source_row is not None else None,
                "superflex_ecr": _json_ready(source_row.get("superflex_ecr")) if source_row is not None else None,
                "dynasty_ecr": _json_ready(source_row.get("dynasty_ecr")) if source_row is not None else None,
                "historical_match": bool(source_row.get("historical_match")) if source_row is not None else False,
                "historical_game_count": len(source_row.get("historical_scores") or []) if source_row is not None else 0,
                "projected_ppg_espn": _json_ready(source_row.get("projected_ppg_espn")) if source_row is not None else None,
                "actual_2025_ppg_espn": _json_ready(source_row.get("actual_2025_ppg_espn")) if source_row is not None else None,
            }
        )
    return audit_rows


def _build_integrity_report(
    *,
    manifest: dict[str, Any],
    match_audit_rows: list[dict[str, Any]],
    league_validations: dict[str, dict[str, Any]],
    history_review_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    history_rows = manifest.get("historyPlayersMatched", 0) + manifest.get("espn2025HistoryFallbackRows", 0)
    usable_rows = manifest.get("usableRows", 0) or 1
    history_coverage = history_rows / usable_rows
    issues: list[str] = []
    warnings: list[str] = []
    if manifest.get("usableRows", 0) < 500:
        issues.append("Usable player pool below 500 rows.")
    if manifest.get("missingByeRows", 0) != 0:
        issues.append("One or more draftable players are missing bye weeks.")
    if history_coverage < 0.75:
        warnings.append(f"History coverage is {history_coverage:.1%}, below 75% review threshold.")

    match_counts = _audit_counts(match_audit_rows)
    fuzzy_review_rows = [
        row for row in match_audit_rows
        if row.get("match_type") == "fuzzy" and row.get("needs_review")
    ]
    if fuzzy_review_rows:
        warnings.append(f"{len(fuzzy_review_rows)} low-confidence fuzzy matches need review.")

    for validation in league_validations.values():
        issues.extend(validation.get("issues", []))
        warnings.extend(validation.get("warnings", []))

    return {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "usableRows": manifest.get("usableRows", 0),
            "historyCoverage": round(history_coverage, 4),
            "missingByeRows": manifest.get("missingByeRows", 0),
            "matchAudit": match_counts,
            "historyReviewRows": len(history_review_rows),
            "leagueValidations": {
                league_id: {
                    "ok": validation.get("ok", False),
                    "rowCount": validation.get("rowCount", 0),
                    "top50Positions": validation.get("top50Positions", {}),
                    "issueCount": len(validation.get("issues", [])),
                    "warningCount": len(validation.get("warnings", [])),
                }
                for league_id, validation in league_validations.items()
            },
        },
    }

def _apply_boosts(df: pd.DataFrame, cfg: LeagueConfig, root: Path) -> pd.DataFrame:
    boost_path = root / "backend" / "player_boost.json"
    if not boost_path.exists():
        return df
    with open(boost_path, "r", encoding="utf-8") as f:
        boost_data = json.load(f)
    tiers = [
        ("max_boost_slugs", cfg.boost_max),
        ("large_boost_slugs", cfg.boost_large),
        ("medium_boost_slugs", cfg.boost_medium),
        ("small_boost_slugs", cfg.boost_small),
    ]
    for key, boost in tiers:
        slugs = set(boost_data.get(key, []))
        if slugs:
            df.loc[df["slug"].isin(slugs), "expected_ppg"] *= 1 + boost
    return df


def _apply_mimics(df: pd.DataFrame, root: Path) -> pd.DataFrame:
    mimic_path = root / "backend" / "player_mimics.json"
    if not mimic_path.exists():
        return df
    with open(mimic_path, "r", encoding="utf-8") as f:
        mimic_map = json.load(f)
    for target_slug, source_slug in mimic_map.items():
        target_rows = df["slug"] == target_slug
        source_rows = df["slug"] == source_slug
        if target_rows.any() and source_rows.any():
            df.loc[target_rows, "expected_ppg"] = df.loc[source_rows, "expected_ppg"].iloc[0]
    return df


def _history_scores_average(scores: Any, top_game_count: int) -> float | None:
    if not isinstance(scores, list):
        return None
    numeric_scores = [score for score in scores if _finite_float(score) is not None]
    return _top_n_average(numeric_scores, top_game_count)


def _history_scores_floor(scores: Any) -> float | None:
    if not isinstance(scores, list):
        return None
    numeric_scores = [score for score in scores if _finite_float(score) is not None]
    return _lower_quartile(numeric_scores)


def _apply_history_window(df: pd.DataFrame, cfg: LeagueConfig) -> pd.DataFrame:
    df = df.copy()
    if "historical_scores" in df.columns:
        df["historical_top_avg"] = df["historical_scores"].map(
            lambda scores: _history_scores_average(scores, cfg.top_game_count)
        )
        df["historical_floor"] = df["historical_scores"].map(_history_scores_floor)

    fallback = df["historical_top_avg"].isna() & df["actual_2025_ppg_espn"].notna()
    df.loc[fallback, "historical_top_avg"] = df.loc[fallback, "actual_2025_ppg_espn"]
    floor_fallback = fallback & df["historical_floor"].isna()
    df.loc[floor_fallback, "historical_floor"] = (
        df.loc[floor_fallback, "actual_2025_ppg_espn"] * 0.75
    )
    return df


def score_players(base: pd.DataFrame, cfg: LeagueConfig, root: Path) -> pd.DataFrame:
    df = _apply_history_window(base, cfg)
    df["z_proj"] = _z_scores(df["projected_ppg"])
    df["z_hist"] = _z_scores(df["historical_top_avg"])
    df["z_floor"] = _z_scores(df["historical_floor"])
    df["scaled_proj"] = _scale_positive(df["z_proj"])
    df["scaled_hist"] = _scale_positive(df["z_hist"])
    df["scaled_floor"] = _scale_positive(df["z_floor"])
    df["scaled_superflex_ecr"] = _scale_inverse_rank(df["superflex_ecr"])
    df["scaled_dynasty_ecr"] = _scale_inverse_rank(df["dynasty_ecr"])

    if cfg.league_type == "guillotine":
        vet = df["scaled_proj"].notna() & df["scaled_floor"].notna()
        rookie = df["scaled_proj"].notna() & df["scaled_floor"].isna()
        history_only = df["scaled_proj"].isna() & df["scaled_floor"].notna()
        df["expected_ppg"] = np.select(
            [vet, rookie, history_only],
            [
                df["scaled_proj"] * cfg.weight_projection
                + df["scaled_floor"] * (cfg.weight_floor or 0),
                df["scaled_proj"],
                df["scaled_floor"],
            ],
            default=0.0,
        )
    else:
        vet = df["scaled_proj"].notna() & df["scaled_hist"].notna()
        rookie = df["scaled_proj"].notna() & df["scaled_hist"].isna()
        history_only = df["scaled_proj"].isna() & df["scaled_hist"].notna()
        df["expected_ppg"] = np.select(
            [vet, rookie, history_only],
            [
                df["scaled_proj"] * cfg.weight_projection
                + df["scaled_hist"] * (cfg.weight_last_year or 0),
                df["scaled_proj"],
                df["scaled_hist"],
            ],
            default=0.0,
        )

    market_total = cfg.weight_superflex_ecr + cfg.weight_dynasty_ecr
    if market_total > 0:
        df["expected_ppg"] = (
            df["expected_ppg"] * (1.0 - market_total)
            + df["scaled_superflex_ecr"].fillna(df["expected_ppg"]) * cfg.weight_superflex_ecr
            + df["scaled_dynasty_ecr"].fillna(df["expected_ppg"]) * cfg.weight_dynasty_ecr
        )

    df = _apply_boosts(df, cfg, root)
    df = _apply_mimics(df, root)
    return df

def calculate_vor(df: pd.DataFrame, cfg: LeagueConfig) -> tuple[pd.DataFrame, dict[str, float]]:
    replacement_levels: dict[str, float] = {}
    active_slots: set[str] = set()
    selected_indexes: set[Any] = set()
    roster = cfg.roster.model_dump()
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
        eligible_positions = slot_eligibility[slot]
        pool = df[
            df["position"].isin(eligible_positions)
            & ~df.index.isin(selected_indexes)
        ].sort_values("expected_ppg", ascending=False)
        demand = cfg.teams * starters
        chosen = pool.iloc[:demand]
        selected_indexes.update(chosen.index.tolist())
        replacement_levels[slot] = (
            float(chosen.iloc[-1]["expected_ppg"])
            if 0 < demand <= len(chosen)
            else 0.0
        )

    position_slots = {
        "QB": ["QB", "SUPERFLEX"],
        "RB": ["RB", "FLEX", "SUPERFLEX"],
        "WR": ["WR", "FLEX", "SUPERFLEX"],
        "TE": ["TE", "FLEX", "SUPERFLEX"],
        "K": ["K"],
        "DEF": ["DEF"],
    }

    def player_vor(row: pd.Series) -> float:
        eligible_slots = [
            slot for slot in position_slots.get(row["position"], [])
            if slot in active_slots
        ]
        replacement_floor = min(
            (replacement_levels.get(slot, 0.0) for slot in eligible_slots),
            default=0.0,
        )
        return float(row["expected_ppg"] - replacement_floor)

    df = df.copy()
    df["vor"] = df.apply(player_vor, axis=1)
    for position, penalty in cfg.positional_penalties.items():
        if penalty < 1.0:
            df.loc[df["position"] == position, "expected_ppg"] *= penalty
            df.loc[df["position"] == position, "vor"] *= penalty
    return df, replacement_levels

def _format_final(df: pd.DataFrame) -> list[dict[str, Any]]:
    final = df.dropna(subset=["adp"]).sort_values("vor", ascending=False).copy()
    final["rank"] = range(1, len(final) + 1)
    rows = []
    for _, row in final.iterrows():
        rows.append(
            {
                "id": int(row["rank"]),
                "name": row["name"],
                "team": row["team"],
                "position": row["position"],
                "adp": round(float(row["adp"]), 1),
                "vor": round(float(row["vor"]), 2),
                "bye": int(row["bye"]),
                "ppg": round(float(row["expected_ppg"]), 2),
                "redraftEcr": round(float(row["redraft_ecr"]), 1) if _finite_float(row.get("redraft_ecr")) is not None else None,
                "superflexEcr": round(float(row["superflex_ecr"]), 1) if _finite_float(row.get("superflex_ecr")) is not None else None,
                "dynastyEcr": round(float(row["dynasty_ecr"]), 1) if _finite_float(row.get("dynasty_ecr")) is not None else None,
            }
        )
    return rows


def build_base_player_pool(root: Path, top_game_count: int) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    espn = fetch_espn_players()
    rankings = fetch_dynastyprocess_rankings()
    player_byes, team_byes = _parse_bye_maps(rankings)
    player_teams = _parse_player_team_map(rankings)
    ranking_maps = _parse_ranking_maps(rankings)
    historical_scores = fetch_last_year_weekly_stats()
    mapped_history, history_match_audit = create_hybrid_slug_map_with_audit(
        historical_scores, espn["slug"].tolist(), score_cutoff=90, review_score_cutoff=95
    )

    espn["projected_ppg"] = espn["projected_ppg_espn"].fillna(
        espn["projected_points"] / 17
    )
    espn["historical_scores"] = espn["slug"].map(lambda slug: mapped_history.get(slug, []))
    espn["historical_match"] = espn["historical_scores"].map(bool)
    espn["historical_top_avg"] = espn["historical_scores"].map(
        lambda scores: _history_scores_average(scores, top_game_count)
    )
    espn["historical_floor"] = espn["historical_scores"].map(_history_scores_floor)
    espn["team"] = espn.apply(
        lambda row: row["team"] or player_teams.get(row["slug"]) or "FA",
        axis=1,
    )
    espn["redraft_ecr"] = espn["slug"].map(ranking_maps["redraft"])
    espn["superflex_ecr"] = espn["slug"].map(ranking_maps["superflex"])
    espn["dynasty_ecr"] = espn["slug"].map(ranking_maps["dynasty"])
    espn["bye"] = espn.apply(
        lambda row: player_byes.get(row["slug"]) or team_byes.get(row["team"]) or 0,
        axis=1,
    )

    keep = (
        espn["position"].isin(["QB", "RB", "WR", "TE", "K", "DEF"])
        & espn["active"]
        & espn["projected_ppg"].notna()
        & espn["adp"].notna()
        & (espn["adp"] <= 360)
        & (espn["bye"] > 0)
    )
    base = espn[keep].copy()
    manifest = {
        "espnRows": int(len(espn)),
        "usableRows": int(len(base)),
        "dynastyProcessRows": int(len(rankings)),
        "dynastyProcessScrapeDates": sorted(str(item) for item in rankings["scrape_date"].dropna().unique().tolist()),
        "historyPlayersMatched": int(base["historical_match"].sum()),
        "espn2025HistoryFallbackRows": int(
            ((~base["historical_match"]) & (base["actual_2025_ppg_espn"].fillna(0) > 0)).sum()
        ),
        "missingHistoryRows": int(
            ((~base["historical_match"]) & (base["actual_2025_ppg_espn"].fillna(0) <= 0)).sum()
        ),
        "baseAuditTopGameCount": top_game_count,
        "missingByeRows": int((base["bye"] <= 0).sum()),
        "sources": {
            "espn": ESPN_PLAYERS_URL,
            "dynastyprocess": DYNASTYPROCESS_RANKINGS_URL,
            "historical": "https://www.fantasypros.com/nfl/stats/{pos}.php?week={week}&scoring=HALF&range=week",
        },
    }
    return base, manifest, history_match_audit


def refresh_all(root: Path | None = None, date_str: str | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    date_str = date_str or dt.date.today().isoformat()
    data_dir = root / "backend" / "data" / date_str
    public_dir = root / "public"
    audit_dir = data_dir / "audits"

    configs = {target.profile_id: _load_config(root / target.config_path) for target in LEAGUE_TARGETS}
    top_game_count = max(config.top_game_count for config in configs.values())
    base, manifest, history_match_audit = build_base_player_pool(root, top_game_count)
    save_json(data_dir / "players_base.json", base.replace({np.nan: None}).to_dict(orient="records"))

    flattened_match_audit = _flatten_match_audit_rows(history_match_audit)
    history_review_rows = _build_history_review_rows(flattened_match_audit, base)
    save_json(audit_dir / "history_match_audit.json", history_match_audit)
    save_csv(
        audit_dir / "history_match_audit.csv",
        flattened_match_audit,
        [
            "canonical_slug",
            "matched_source_slug",
            "match_type",
            "score",
            "needs_review",
            "review_reason",
            "review_scope",
            "name",
            "team",
            "position",
            "adp",
            "espn_rank",
            "alternatives",
        ],
    )
    save_csv(
        audit_dir / "history_match_review.csv",
        history_review_rows,
        [
            "canonical_slug",
            "matched_source_slug",
            "match_type",
            "score",
            "needs_review",
            "review_reason",
            "review_scope",
            "name",
            "team",
            "position",
            "adp",
            "espn_rank",
            "alternatives",
        ],
    )

    league_summaries = {}
    league_validations = {}
    for target in LEAGUE_TARGETS:
        cfg = configs[target.profile_id]
        scored = score_players(base, cfg, root)
        with_vor, replacement_levels = calculate_vor(scored, cfg)
        rows = _format_final(with_vor)
        top_audit_rows = _top_player_audit_rows(with_vor, rows)
        save_csv(
            audit_dir / f"top50_{target.profile_id}.csv",
            top_audit_rows,
            [
                "rank",
                "name",
                "team",
                "position",
                "adp",
                "vor",
                "ppg",
                "bye",
                "espn_rank",
                "redraft_ecr",
                "superflex_ecr",
                "dynasty_ecr",
                "historical_match",
                "historical_game_count",
                "projected_ppg_espn",
                "actual_2025_ppg_espn",
            ],
        )
        validation = _validate_final_rows(rows, target.profile_id)
        league_validations[target.profile_id] = validation
        save_json(data_dir / target.profile_id / "players_final.json", rows)
        save_json(public_dir / target.public_file, rows)
        league_summaries[target.profile_id] = {
            "label": target.label,
            "file": target.public_file,
            "count": len(rows),
            "replacementLevels": replacement_levels,
            "top10": rows[:10],
            "validation": validation,
        }

    integrity_report = _build_integrity_report(
        manifest=manifest,
        match_audit_rows=history_match_audit,
        league_validations=league_validations,
        history_review_rows=history_review_rows,
    )
    save_json(audit_dir / "integrity_report.json", integrity_report)
    if not integrity_report["ok"]:
        raise RuntimeError(
            "Data integrity checks failed. Review "
            f"{audit_dir / 'integrity_report.json'} before using public JSON files."
        )

    status = {
        "status": "draft-ready",
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "label": f"{date_str} refresh",
        "message": "2026 data refreshed from ESPN ADP/projections, DynastyProcess rankings/byes, and FantasyPros historical weekly stats.",
        "files": {target.public_file: target.label for target in LEAGUE_TARGETS},
        "sources": manifest["sources"],
        "integrity": integrity_report["summary"],
    }
    save_json(public_dir / "data_status.json", status)
    full_manifest = {
        "generatedAt": status["generatedAt"],
        "date": date_str,
        **manifest,
        "integrity": integrity_report,
        "leagues": league_summaries,
        "auditFiles": {
            "historyMatchAuditCsv": str(audit_dir / "history_match_audit.csv"),
            "historyMatchReviewCsv": str(audit_dir / "history_match_review.csv"),
            "integrityReportJson": str(audit_dir / "integrity_report.json"),
            "top50CsvPattern": str(audit_dir / "top50_<league>.csv"),
        },
    }
    save_json(data_dir / "refresh_manifest.json", full_manifest)
    return full_manifest