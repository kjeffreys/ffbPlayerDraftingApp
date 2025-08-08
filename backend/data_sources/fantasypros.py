# backend/data_sources/fantasypros.py (Consolidated & Consistent)
import io
import re
import pandas as pd
import requests

# Local application imports
try:
    from backend.logging_config import log
    from backend.settings import settings
    from backend.utils import slugify
except ImportError:
    # This block is for standalone testing only
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


# --- ADP Scraper (Now with Dynamic URL) ---
def fetch_adp() -> dict[str, tuple[float, int | None]]:
    """
    Scrapes FantasyPros ADP and returns ADP and Bye Week for each player.
    The URL is now dynamically chosen based on the scoring setting.
    """
    scoring_map = {
        "PPR": "ppr-overall.php",
        "HALF": "half-ppr-overall.php",
        "STD": "std-overall.php",
    }
    scoring_setting = settings.league_config.scoring.upper()

    if scoring_setting not in scoring_map:
        log.error(
            f"Invalid scoring setting for ADP URL: '{scoring_setting}'. Defaulting to HALF."
        )
        scoring_setting = "HALF"

    url_path = scoring_map[scoring_setting]
    url = f"https://www.fantasypros.com/nfl/adp/{url_path}"

    log.info("Fetching ADP and Bye Week data from FantasyPros.", extra={"url": url})
    # The rest of the function remains the same as it was already working
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text), attrs={"id": "data"})
        if not tables:
            raise ValueError("ADP table not found.")
        df = tables[0]

        player_col, adp_col = "Player Team (Bye)", "AVG"
        if player_col not in df.columns or adp_col not in df.columns:
            log.error(
                f"Required ADP columns not found. Discovered: {df.columns.tolist()}"
            )
            return {}

        adp_map = {}
        for _, row in df.iterrows():
            player_info = row[player_col]
            bye_match = re.search(r"\((\d+)\)", player_info)
            bye_week = int(bye_match.group(1)) if bye_match else None
            name_parts = player_info.split()
            player_name = (
                " ".join(name_parts[:-2])
                if len(name_parts) > 2
                else (name_parts[0] if name_parts else "")
            )
            if player_name:
                adp_map[slugify(player_name)] = (float(row[adp_col]), bye_week)

        log.info(f"Successfully parsed ADP and Bye Weeks for {len(adp_map)} players.")
        return adp_map
    except Exception as e:
        log.exception(
            "Failed to fetch or parse ADP/Bye Week data.", extra={"error": str(e)}
        )
        raise


# --- Projections Scraper (No changes needed here) ---
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
