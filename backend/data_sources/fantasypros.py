# backend/backend/data_sources/fantasypros.py
"""Data source for scraping ADP from FantasyPros."""


import pandas as pd
import requests

from logging_config import setup_logging
from settings import settings
from utils import slugify

log = setup_logging(__name__)


def fetch_adp() -> dict[str, float]:
    """
    Scrapes the FantasyPros PPR ADP page and returns a mapping of
    player names to their overall ADP.

    Returns:
        A dictionary mapping a slugified player name to their ADP, e.g.,
        {"patrick-mahomes": 28.5}.
    """
    url = settings.FANTASYPROS_ADP_URL
    log.info("Fetching ADP data from FantasyPros.", extra={"url": url})

    try:
        # FantasyPros often blocks simple requests, so we add a basic user-agent.
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # pandas.read_html is brilliant for parsing tables
        tables = pd.read_html(response.text, attrs={"id": "data"})
        if not tables:
            log.error("Could not find ADP table on page.")
            raise ValueError("ADP table with id='data' not found.")

        df = tables[0]
        # Clean up column names which can have multiple levels
        df.columns = ["_".join(col).strip() for col in df.columns.values]

        # We only need player name and their overall ADP
        adp_data = df[["Player Team_Player", "Overall_AVG"]]

        adp_map = {}
        for _, row in adp_data.iterrows():
            # The player name is in a column like "Patrick Mahomes KC"
            # We want to extract just the name.
            player_name = " ".join(row["Player Team_Player"].split()[:-1])
            player_slug = slugify(player_name)
            adp_map[player_slug] = float(row["Overall_AVG"])

        log.info("Successfully parsed ADP data.", extra={"player_count": len(adp_map)})
        return adp_map

    except (requests.RequestException, ValueError, KeyError) as e:
        log.exception(
            "Failed to fetch or parse ADP data.", extra={"url": url, "error": str(e)}
        )
        raise
