"""Diagnostics for fragile external fantasy-football data sources."""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from backend.refresh_data import (
    DYNASTYPROCESS_RANKINGS_URL,
    ESPN_PLAYERS_URL,
    ESPN_POSITION_MAP,
    _espn_filter,
)
from backend.storage.file_store import save_json


HEADERS = {"User-Agent": "Mozilla/5.0"}


def _flatten_columns(df: pd.DataFrame) -> list[str]:
    if isinstance(df.columns, pd.MultiIndex):
        return [
            "_".join(str(part) for part in col if str(part) != "nan").strip()
            for col in df.columns
        ]
    return [str(col).strip() for col in df.columns]


def table_has_keywords(columns: list[str], keywords: list[str]) -> bool:
    lowered = [column.lower() for column in columns]
    return all(
        any(keyword.lower() in column for column in lowered) for keyword in keywords
    )


def _read_tables(html: str, attrs: dict[str, str] | None) -> list[pd.DataFrame]:
    try:
        if attrs:
            return pd.read_html(io.StringIO(html), attrs=attrs)
    except (ImportError, ValueError):
        pass
    return pd.read_html(io.StringIO(html))


def check_html_table(
    *,
    name: str,
    url: str,
    required_column_keywords: list[str],
    min_rows: int = 10,
    attrs: dict[str, str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "url": url,
        "ok": False,
        "requiredColumnKeywords": required_column_keywords,
        "minRows": min_rows,
    }
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        result["httpStatus"] = response.status_code
        response.raise_for_status()
        tables = _read_tables(response.text, attrs)
        result["tableCount"] = len(tables)
        for index, table in enumerate(tables):
            columns = _flatten_columns(table)
            if len(table) >= min_rows and table_has_keywords(
                columns, required_column_keywords
            ):
                result.update(
                    {
                        "ok": True,
                        "matchedTableIndex": index,
                        "rowCount": int(len(table)),
                        "columns": columns,
                    }
                )
                return result
        result["error"] = "No table matched required columns and row threshold."
        result["candidateTables"] = [
            {
                "index": index,
                "rowCount": int(len(table)),
                "columns": _flatten_columns(table),
                "hasRequiredColumns": table_has_keywords(
                    _flatten_columns(table), required_column_keywords
                ),
            }
            for index, table in enumerate(tables[:3])
        ]
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _has_stat(player: dict[str, Any], stat_id: str) -> bool:
    return any(stat.get("id") == stat_id for stat in player.get("stats", []))


def check_espn_current_players() -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": "espn_2026_players",
        "url": ESPN_PLAYERS_URL,
        "ok": False,
        "minRows": 500,
    }
    try:
        response = requests.get(
            ESPN_PLAYERS_URL,
            headers={**HEADERS, "x-fantasy-filter": _espn_filter()},
            timeout=30,
        )
        result["httpStatus"] = response.status_code
        response.raise_for_status()
        players = response.json().get("players", [])
        parsed = [item.get("player", {}) for item in players]
        fantasy_positions = [
            player
            for player in parsed
            if player.get("defaultPositionId") in ESPN_POSITION_MAP
        ]
        with_adp = [
            player
            for player in fantasy_positions
            if (player.get("ownership") or {}).get("averageDraftPosition")
        ]
        with_projection = [
            player for player in fantasy_positions if _has_stat(player, "102026")
        ]
        position_counts: dict[str, int] = {}
        for player in fantasy_positions:
            position = ESPN_POSITION_MAP[player.get("defaultPositionId")]
            position_counts[position] = position_counts.get(position, 0) + 1
        result.update(
            {
                "rowCount": len(fantasy_positions),
                "adpRows": len(with_adp),
                "projectionRows": len(with_projection),
                "positionCounts": position_counts,
                "ok": len(fantasy_positions) >= 500
                and len(with_adp) >= 300
                and len(with_projection) >= 300,
            }
        )
        if not result["ok"]:
            result["error"] = "ESPN payload did not meet row, ADP, or projection thresholds."
    except Exception as exc:
        result["error"] = str(exc)
    return result


def check_dynastyprocess_rankings() -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": "dynastyprocess_rankings",
        "url": DYNASTYPROCESS_RANKINGS_URL,
        "ok": False,
        "minRows": 3000,
    }
    try:
        response = requests.get(DYNASTYPROCESS_RANKINGS_URL, headers=HEADERS, timeout=30)
        result["httpStatus"] = response.status_code
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        required_columns = {"player", "page_type", "ecr", "bye", "scrape_date"}
        missing_columns = sorted(required_columns - set(df.columns))
        page_types = set(df.get("page_type", pd.Series(dtype=str)).dropna().astype(str))
        required_pages = {"redraft-overall", "redraft-op", "dynasty-overall"}
        missing_pages = sorted(required_pages - page_types)
        scrape_dates = sorted(
            str(item) for item in df.get("scrape_date", pd.Series(dtype=str)).dropna().unique().tolist()
        )
        bye_rows = int(df.get("bye", pd.Series(dtype=float)).notna().sum())
        result.update(
            {
                "rowCount": int(len(df)),
                "columns": list(df.columns),
                "scrapeDates": scrape_dates,
                "byeRows": bye_rows,
                "missingColumns": missing_columns,
                "missingPageTypes": missing_pages,
                "ok": len(df) >= 3000
                and not missing_columns
                and not missing_pages
                and bye_rows >= 300,
            }
        )
        if not result["ok"]:
            result["error"] = "DynastyProcess rankings are missing required rows, columns, page types, or bye values."
    except Exception as exc:
        result["error"] = str(exc)
    return result


def run_source_diagnostics(
    scoring: str = "HALF", output_path: Path | None = None
) -> dict[str, Any]:
    scoring = scoring.upper()
    checks = [check_espn_current_players(), check_dynastyprocess_rankings()]

    for position in ["qb", "rb", "wr", "te"]:
        checks.append(
            check_html_table(
                name=f"fantasypros_history_{position}_week1",
                url=f"https://www.fantasypros.com/nfl/stats/{position}.php?week=1&scoring={scoring}&range=week",
                required_column_keywords=["Player", "FPTS"],
                min_rows=20,
            )
        )

    manifest = {
        "checkedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scoring": scoring,
        "ok": all(check.get("ok") for check in checks),
        "checks": checks,
    }
    if output_path:
        save_json(output_path, manifest)
    return manifest

