# Path: ffbPlayerDraftingApp/backend/data_sources/historical.py

import io
import time
import pandas as pd
import requests
import re
import datetime

from backend.logging_config import log
from backend.utils import slugify
from backend.storage.file_store import save_json
from backend.settings import settings

BASE_URL = "https://www.fantasypros.com/nfl/stats/{pos}.php?week={week}&scoring=HALF&range=week"
POSITIONS = ["qb", "rb", "wr", "te", "k", "dst"]
WEEKS = range(1, 18)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def _parse_table(df: pd.DataFrame) -> dict[str, float]:
    weekly_scores = {}
    try:
        player_col_header = next(col for col in df.columns if "Player" in str(col))
        fpts_col_header = next(col for col in df.columns if "FPTS" in str(col))
    except StopIteration:
        return {}

    for _, row in df.iterrows():
        player_info_str = str(row[player_col_header]).strip()

        clean_name = player_info_str.replace("*", "").replace("+", "").strip()
        clean_name = re.sub(r"\s+[A-Z]{2,3}$", "", clean_name).strip()
        player_slug = slugify(clean_name)

        try:
            score = float(row[fpts_col_header])
            if player_slug:
                weekly_scores[player_slug] = score
        except (ValueError, TypeError):
            continue
    return weekly_scores


def fetch_last_year_weekly_stats() -> dict[str, list[float]]:
    log.info("Starting historical data scrape.")
    all_player_scores: dict[str, list[float]] = {}
    for pos in POSITIONS:
        pos_scores: dict[str, list[float]] = {}
        for week in WEEKS:
            url = BASE_URL.format(pos=pos, week=week)
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                tables = pd.read_html(io.StringIO(response.text))
                if tables:
                    weekly_scores = _parse_table(tables[0])
                    for slug, score in weekly_scores.items():
                        pos_scores.setdefault(slug, []).append(score)
                time.sleep(0.25)
            except Exception as e:
                log.error(
                    f"Error processing {pos.upper()} Week {week}.",
                    extra={"error": str(e)},
                )

        for slug, scores in pos_scores.items():
            if slug not in all_player_scores:
                all_player_scores[slug] = scores

    log.info(
        f"Finished scraping historical data for {len(all_player_scores)} unique players."
    )
    return all_player_scores
