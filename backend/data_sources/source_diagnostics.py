"""Diagnostics for fragile external fantasy-football data sources."""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path
from typing import Any

import pandas as pd
import requests

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
    except ImportError:
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


def fantasypros_adp_url(scoring: str) -> str:
    scoring_map = {
        "PPR": "ppr-overall.php",
        "HALF": "half-point-ppr-overall.php",
        "STD": "std-overall.php",
    }
    return f"https://www.fantasypros.com/nfl/adp/{scoring_map.get(scoring.upper(), scoring_map['HALF'])}"


def run_source_diagnostics(
    scoring: str = "HALF", output_path: Path | None = None
) -> dict[str, Any]:
    checks = [
        check_html_table(
            name="fantasypros_adp",
            url=fantasypros_adp_url(scoring),
            attrs={"id": "data"},
            required_column_keywords=["Player", "AVG"],
            min_rows=100,
        )
    ]

    for position in ["qb", "rb", "wr", "te", "k", "dst"]:
        checks.append(
            check_html_table(
                name=f"fantasypros_projection_{position}",
                url=f"https://www.fantasypros.com/nfl/projections/{position}.php?scoring={scoring.upper()}&week=0",
                required_column_keywords=["Player", "FPTS"],
                min_rows=20 if position not in {"k", "dst"} else 10,
            )
        )

    for position in ["qb", "rb", "wr", "te"]:
        checks.append(
            check_html_table(
                name=f"fantasypros_history_{position}_week1",
                url=f"https://www.fantasypros.com/nfl/stats/{position}.php?week=1&scoring={scoring.upper()}&range=week",
                required_column_keywords=["Player", "FPTS"],
                min_rows=20,
            )
        )

    manifest = {
        "checkedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scoring": scoring.upper(),
        "ok": all(check.get("ok") for check in checks),
        "checks": checks,
    }
    if output_path:
        save_json(output_path, manifest)
    return manifest