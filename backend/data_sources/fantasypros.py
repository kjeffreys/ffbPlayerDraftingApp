# backend/data_sources/fantasypros.py (Consolidated & Consistent)
import io
import re
import pandas as pd
import requests

try:
    from backend.logging_config import log
    from backend.settings import settings
    from backend.utils import slugify
except ImportError:
    import logging

    log = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    class DummySettings:
        class DummyLeagueConfig:
            scoring = "HALF"

        league_config = DummyLeagueConfig()

    settings = DummySettings()

    def slugify(text):
        text = str(text).lower().strip()
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"[\s-]+", "-", text).strip("-")
        return text


def _parse_adp_player_name(player_info: str) -> str:
    clean = re.sub(r"\s+\(\d+\)$", "", str(player_info)).strip()
    clean = re.sub(r"\s+[A-Z]{2,3}$", "", clean).strip()
    duplicate_short_name = re.search(r"\s+[A-Z]\.\s+", clean)
    if duplicate_short_name:
        return clean[: duplicate_short_name.start()].strip()
    return clean


def fetch_adp() -> dict[str, tuple[float, int | None]]:
    """Scrape FantasyPros ADP and return ADP plus bye week by player slug."""
    scoring_map = {
        "PPR": "ppr-overall.php",
        "HALF": "half-point-ppr-overall.php",
        "STD": "std-overall.php",
    }
    scoring_setting = settings.league_config.scoring.upper()

    if scoring_setting not in scoring_map:
        log.error(
            f"Invalid scoring setting for ADP URL: '{scoring_setting}'. Defaulting to HALF."
        )
        scoring_setting = "HALF"

    url = f"https://www.fantasypros.com/nfl/adp/{scoring_map[scoring_setting]}"
    log.info("Fetching ADP and Bye Week data from FantasyPros.", extra={"url": url})
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        adp_col = "AVG"
        tables = pd.read_html(io.StringIO(response.text))
        df = next(
            (
                table
                for table in tables
                if any("Player" in str(column) for column in table.columns)
                and adp_col in table.columns
            ),
            None,
        )
        if df is None:
            discovered = [table.columns.tolist() for table in tables[:3]]
            log.error(f"Required ADP columns not found. Discovered: {discovered}")
            return {}

        player_col = next(column for column in df.columns if "Player" in str(column))
        adp_map = {}
        for _, row in df.iterrows():
            player_info = str(row[player_col])
            bye_match = re.search(r"\((\d+)\)", player_info)
            bye_week = int(bye_match.group(1)) if bye_match else None
            player_name = _parse_adp_player_name(player_info)
            if player_name:
                adp_map[slugify(player_name)] = (float(row[adp_col]), bye_week)

        log.info(f"Successfully parsed ADP and Bye Weeks for {len(adp_map)} players.")
        return adp_map
    except Exception as e:
        log.exception(
            "Failed to fetch or parse ADP/Bye Week data.", extra={"error": str(e)}
        )
        raise


def fetch_projections_by_position(position: str, scoring: str) -> pd.DataFrame:
    url = f"https://www.fantasypros.com/nfl/projections/{position.lower()}.php?scoring={scoring.upper()}&week=0"
    log.info(f"Fetching projections for position '{position}' from {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        df = pd.read_html(io.StringIO(response.text))[0]

        player_col, fpts_col = None, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join(col).strip() for col in df.columns]
            player_col, fpts_col = "Unnamed: 0_level_0_Player", "MISC_FPTS"
        else:
            player_col, fpts_col = "Player", "FPTS"

        if player_col not in df.columns or fpts_col not in df.columns:
            return pd.DataFrame()

        df["player_slug"] = (
            df[player_col]
            .str.replace(r"\s+[A-Z]{2,3}$", "", regex=True)
            .str.strip()
            .apply(slugify)
        )
        final_df = (
            df[["player_slug", fpts_col]]
            .copy()
            .rename(columns={fpts_col: "projection_fpts"})
        )
        final_df.dropna(subset=["player_slug"], inplace=True)
        final_df = final_df[final_df.player_slug != ""]
        return final_df
    except Exception:
        return pd.DataFrame()


def fetch_all_projections() -> pd.DataFrame:
    positions = ["QB", "RB", "WR", "TE", "K", "DST"]
    scoring = settings.league_config.scoring
    all_dfs = [fetch_projections_by_position(pos, scoring) for pos in positions]
    combined_df = pd.concat([df for df in all_dfs if not df.empty], ignore_index=True)
    log.info(
        f"Successfully combined projections. Total players/teams: {len(combined_df)}"
    )
    return combined_df
