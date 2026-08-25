import csv
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pydantic import ValidationError

from backend.history_store import import_csv, init_db, manager_tendencies
from backend.data_sources.fantasypros import _parse_adp_player_name
from backend.data_sources.source_diagnostics import table_has_keywords
from backend.pipelines.stats import normalize_boost_data
from backend.settings import LeagueConfig
from backend.refresh_data import _validate_final_rows, calculate_vor
from backend.utils import create_hybrid_slug_map_with_audit


BASE_CONFIG = {
    "teams": 12,
    "roster": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DEF": 1},
    "scoring": "HALF",
    "week": 1,
    "games_divisor": 17,
    "boost_small": 0.05,
    "boost_medium": 0.1,
    "boost_large": 0.15,
    "boost_max": 0.25,
    "top_game_count": 8,
    "weight_projection": 0.5,
    "weight_last_year": 0.5,
    "min_historical_score": 0.0,
    "positional_penalties": {"K": 0.5, "DEF": 0.5},
}


class ConfigAndHistoryTests(unittest.TestCase):
    def test_config_rejects_unknown_keys(self):
        config = dict(BASE_CONFIG, unexpected=True)
        with self.assertRaises(ValidationError):
            LeagueConfig(**config)

    def test_guillotine_requires_floor_weight(self):
        config = dict(BASE_CONFIG, league_type="guillotine")
        config.pop("weight_last_year")
        with self.assertRaises(ValidationError):
            LeagueConfig(**config)

    def test_guillotine_accepts_floor_weight(self):
        config = dict(BASE_CONFIG, league_type="guillotine", weight_floor=0.6)
        config["weight_projection"] = 0.4
        config.pop("weight_last_year")
        parsed = LeagueConfig(**config)
        self.assertEqual(parsed.league_type, "guillotine")
        self.assertEqual(parsed.weight_floor, 0.6)


    def test_market_weights_are_bounded(self):
        config = dict(BASE_CONFIG, weight_superflex_ecr=0.35, weight_dynasty_ecr=0.2)
        with self.assertRaises(ValidationError):
            LeagueConfig(**config)

    def test_legacy_boost_keys_are_normalized(self):
        boost_data = normalize_boost_data(
            {
                "large-boost": ["a-player"],
                "large_boost_slugs": ["b-player"],
                "small-boost": ["c-player"],
            }
        )
        self.assertEqual(boost_data["large_boost_slugs"], ["a-player", "b-player"])
        self.assertEqual(boost_data["small_boost_slugs"], ["c-player"])

    def test_adp_player_name_parser_removes_duplicate_short_name(self):
        self.assertEqual(
            _parse_adp_player_name("Bijan Robinson B. Robinson ATL (11)"),
            "Bijan Robinson",
        )
        self.assertEqual(
            _parse_adp_player_name("Amon-Ra St. Brown A. St. Brown DET (6)"),
            "Amon-Ra St. Brown",
        )

    def test_source_column_keyword_matching(self):
        columns = ["Player Team (Bye)", "AVG", "Sleeper"]
        self.assertTrue(table_has_keywords(columns, ["Player", "AVG"]))
        self.assertFalse(table_has_keywords(columns, ["Player", "FPTS"]))

    def test_history_csv_import_and_tendencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "history.sqlite"
            csv_path = root / "draft.csv"
            init_db(db_path)
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "pick_no",
                        "round_no",
                        "manager",
                        "player_name",
                        "nfl_team",
                        "position",
                        "adp_at_pick",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "pick_no": 12,
                        "round_no": 1,
                        "manager": "Bills Fan",
                        "player_name": "Josh Allen",
                        "nfl_team": "BUF",
                        "position": "QB",
                        "adp_at_pick": 20,
                    }
                )

            count = import_csv(db_path, csv_path, "vany", 2025, "sleeper")
            rows = manager_tendencies(db_path)
            self.assertEqual(count, 1)
            self.assertEqual(rows[0]["manager"], "Bills Fan")
            self.assertEqual(rows[0]["favorite_nfl_teams"], [("BUF", 1)])



    def test_hybrid_slug_map_returns_reviewable_audit(self):
        mapped, audit_rows = create_hybrid_slug_map_with_audit(
            {
                "direct-player": [1.0],
                "aaron-jones-sr": [2.0],
                "jamarr-chase-cin": [3.0],
                "stray-source": [4.0],
            },
            ["direct-player", "aaron-jones", "jamarr-chase", "missing-player"],
        )
        self.assertEqual(mapped["direct-player"], [1.0])
        self.assertEqual(mapped["aaron-jones"], [2.0])
        self.assertEqual(mapped["jamarr-chase"], [3.0])

        by_type = {}
        for row in audit_rows:
            by_type[row["match_type"]] = by_type.get(row["match_type"], 0) + 1
        self.assertEqual(by_type["direct"], 1)
        self.assertEqual(by_type["alias"], 1)
        self.assertEqual(by_type["fuzzy"], 1)
        self.assertEqual(by_type["unmatched_canonical"], 1)
        self.assertEqual(by_type["unmatched_source"], 1)
        missing_row = next(row for row in audit_rows if row["canonical_slug"] == "missing-player")
        self.assertEqual(missing_row["match_type"], "unmatched_canonical")
        self.assertFalse(missing_row["needs_review"])


    def test_superflex_vor_uses_lineup_slots(self):
        config = dict(BASE_CONFIG)
        config["teams"] = 2
        config["roster"] = {
            "QB": 1,
            "RB": 1,
            "WR": 1,
            "TE": 0,
            "FLEX": 1,
            "SUPERFLEX": 1,
            "K": 0,
            "DEF": 0,
        }
        parsed = LeagueConfig(**config)
        players = pd.DataFrame(
            [
                {"name": "QB1", "position": "QB", "expected_ppg": 30.0},
                {"name": "QB2", "position": "QB", "expected_ppg": 20.0},
                {"name": "QB3", "position": "QB", "expected_ppg": 19.0},
                {"name": "QB4", "position": "QB", "expected_ppg": 18.0},
                {"name": "RB1", "position": "RB", "expected_ppg": 22.0},
                {"name": "RB2", "position": "RB", "expected_ppg": 16.0},
                {"name": "RB3", "position": "RB", "expected_ppg": 15.0},
                {"name": "WR1", "position": "WR", "expected_ppg": 21.0},
                {"name": "WR2", "position": "WR", "expected_ppg": 14.0},
                {"name": "WR3", "position": "WR", "expected_ppg": 13.0},
            ]
        )

        with_vor, replacement_levels = calculate_vor(players, parsed)
        by_name = with_vor.set_index("name")

        self.assertEqual(replacement_levels["QB"], 20.0)
        self.assertEqual(replacement_levels["SUPERFLEX"], 18.0)
        self.assertEqual(replacement_levels["FLEX"], 13.0)
        self.assertEqual(by_name.loc["QB1", "vor"], 12.0)
        self.assertEqual(by_name.loc["RB1", "vor"], 9.0)
        self.assertEqual(by_name.loc["WR1", "vor"], 8.0)

    def test_final_row_validator_catches_integrity_errors(self):
        valid_rows = [
            {
                "id": index,
                "name": f"Player {index}",
                "team": "BUF",
                "position": "RB" if index <= 25 else "WR",
                "adp": float(index),
                "vor": 50.0 - index,
                "bye": 7,
                "ppg": 20.0 - (index / 10),
            }
            for index in range(1, 301)
        ]
        self.assertTrue(_validate_final_rows(valid_rows, "test")["ok"])

        broken_rows = [dict(row) for row in valid_rows]
        broken_rows[0]["id"] = 99
        broken_rows[1]["bye"] = 0
        validation = _validate_final_rows(broken_rows, "test")
        self.assertFalse(validation["ok"])
        self.assertGreaterEqual(len(validation["issues"]), 2)

if __name__ == "__main__":
    unittest.main()
