"""Local-only draft history storage and import helpers."""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from backend.utils import slugify


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DraftPickRecord:
    league_key: str
    season: int
    platform: str
    pick_no: int
    round_no: int | None
    manager: str
    player_name: str
    player_slug: str
    nfl_team: str | None = None
    position: str | None = None
    source: str = "manual"
    external_player_id: str | None = None
    adp_at_pick: float | None = None


def default_db_path(root_dir: Path) -> Path:
    return root_dir / "local" / "draft_history.sqlite"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    with closing(connect(db_path)) as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS draft_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_key TEXT NOT NULL,
                season INTEGER NOT NULL,
                platform TEXT NOT NULL,
                pick_no INTEGER NOT NULL,
                round_no INTEGER,
                manager TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_slug TEXT NOT NULL,
                nfl_team TEXT,
                position TEXT,
                source TEXT NOT NULL,
                external_player_id TEXT,
                adp_at_pick REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(league_key, season, platform, pick_no, source)
            );

            CREATE INDEX IF NOT EXISTS idx_draft_picks_league
                ON draft_picks(league_key, season, platform);

            CREATE INDEX IF NOT EXISTS idx_draft_picks_player
                ON draft_picks(player_slug);
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        conn.commit()


def upsert_pick(db_path: Path, pick: DraftPickRecord) -> None:
    init_db(db_path)
    with closing(connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO draft_picks (
                league_key, season, platform, pick_no, round_no, manager,
                player_name, player_slug, nfl_team, position, source,
                external_player_id, adp_at_pick
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(league_key, season, platform, pick_no, source)
            DO UPDATE SET
                round_no = excluded.round_no,
                manager = excluded.manager,
                player_name = excluded.player_name,
                player_slug = excluded.player_slug,
                nfl_team = excluded.nfl_team,
                position = excluded.position,
                external_player_id = excluded.external_player_id,
                adp_at_pick = excluded.adp_at_pick
            """,
            (
                pick.league_key,
                pick.season,
                pick.platform,
                pick.pick_no,
                pick.round_no,
                pick.manager,
                pick.player_name,
                pick.player_slug,
                pick.nfl_team,
                pick.position,
                pick.source,
                pick.external_player_id,
                pick.adp_at_pick,
            ),
        )
        conn.commit()


def import_csv(
    db_path: Path, csv_path: Path, league_key: str, season: int, platform: str
) -> int:
    """Import a manual draft history CSV into the local SQLite store."""
    count = 0
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            player_name = row.get("player_name") or row.get("name") or ""
            pick = DraftPickRecord(
                league_key=league_key,
                season=season,
                platform=platform,
                pick_no=int(row["pick_no"]),
                round_no=_maybe_int(row.get("round_no")),
                manager=row.get("manager") or row.get("team") or "Unknown",
                player_name=player_name,
                player_slug=row.get("player_slug") or slugify(player_name),
                nfl_team=_clean_optional(row.get("nfl_team")),
                position=_clean_optional(row.get("position")),
                source="csv",
                external_player_id=_clean_optional(row.get("external_player_id")),
                adp_at_pick=_maybe_float(row.get("adp_at_pick")),
            )
            upsert_pick(db_path, pick)
            count += 1
    return count


def import_sleeper_draft(
    db_path: Path, draft_id: str, league_key: str, season: int
) -> int:
    """Import public Sleeper draft picks by draft ID."""
    url = f"https://api.sleeper.app/v1/draft/{draft_id}/picks"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    picks: list[dict[str, Any]] = response.json()

    for raw_pick in picks:
        metadata = raw_pick.get("metadata") or {}
        first_name = metadata.get("first_name") or ""
        last_name = metadata.get("last_name") or ""
        player_name = " ".join(part for part in [first_name, last_name] if part)
        if not player_name:
            player_name = metadata.get("player_name") or raw_pick.get("player_id") or ""

        pick = DraftPickRecord(
            league_key=league_key,
            season=season,
            platform="sleeper",
            pick_no=int(raw_pick["pick_no"]),
            round_no=_maybe_int(raw_pick.get("round")),
            manager=str(raw_pick.get("picked_by") or raw_pick.get("roster_id") or "Unknown"),
            player_name=player_name,
            player_slug=slugify(player_name),
            nfl_team=_clean_optional(metadata.get("team")),
            position=_clean_optional(metadata.get("position")),
            source="sleeper_api",
            external_player_id=_clean_optional(raw_pick.get("player_id")),
        )
        upsert_pick(db_path, pick)

    return len(picks)


def export_json(db_path: Path, output_path: Path) -> int:
    init_db(db_path)
    with closing(connect(db_path)) as conn:
        rows = [
            dict(row)
            for row in conn.execute("SELECT * FROM draft_picks ORDER BY season, pick_no")
        ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": SCHEMA_VERSION, "draft_picks": rows}, f, indent=2)
    return len(rows)


def manager_tendencies(db_path: Path) -> list[dict[str, Any]]:
    """Return simple local tendency summaries for imported draft history."""
    init_db(db_path)
    with closing(connect(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT
                manager,
                COUNT(*) AS pick_count,
                AVG(CASE WHEN adp_at_pick IS NOT NULL THEN adp_at_pick - pick_no END)
                    AS avg_adp_reach,
                GROUP_CONCAT(nfl_team) AS nfl_teams
            FROM draft_picks
            GROUP BY manager
            ORDER BY pick_count DESC, manager ASC
            """
        ).fetchall()

    return [_format_tendency(dict(row)) for row in rows]


def write_csv_template(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "pick_no",
        "round_no",
        "manager",
        "player_name",
        "player_slug",
        "nfl_team",
        "position",
        "external_player_id",
        "adp_at_pick",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()


def _format_tendency(row: dict[str, Any]) -> dict[str, Any]:
    team_counts: dict[str, int] = {}
    for team in (row.pop("nfl_teams") or "").split(","):
        if team:
            team_counts[team] = team_counts.get(team, 0) + 1
    row["favorite_nfl_teams"] = sorted(
        team_counts.items(), key=lambda item: item[1], reverse=True
    )[:5]
    return row


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _maybe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _maybe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
