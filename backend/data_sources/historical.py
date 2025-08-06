# Path: ffbPlayerDraftingApp/backend/data_sources/historical.py

import io, time, pandas as pd, requests
from backend.logging_config import log
from backend.utils import slugify

BASE_URL = "https://www.fantasypros.com/nfl/stats/{pos}.php?week={week}&scoring=HALF&range=week"
POSITIONS = ["qb", "rb", "wr", "te", "k", "dst"]
WEEKS = range(1, 18)


def fetch_last_year_weekly_stats() -> dict[str, list[float]]:
    log.info("Starting weekly historical data scrape.")
    all_player_scores: dict[str, list[float]] = {}
    headers = {"User-Agent": "Mozilla/5.0..."}
    for pos in POSITIONS:
        for week in WEEKS:
            url = BASE_URL.format(pos=pos, week=week)
            log.info(f"Fetching {pos.upper()} stats for Week {week}...")
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                tables = pd.read_html(io.StringIO(response.text))
                if not tables:
                    continue
                df = tables[0]

                # --- THE DEFINITIVE FIX ---
                # The logs PROVE the headers are multi-level. We must handle them.
                # Find the player and FPTS columns, which are tuples.
                player_col = next((col for col in df.columns if "Player" in col), None)
                fpts_col = next((col for col in df.columns if "FPTS" in col), None)

                if not player_col or not fpts_col:
                    log.warning(
                        f"Required columns not found for {pos.upper()} Week {week}."
                    )
                    continue

                for _, row in df.iterrows():
                    player_name = (
                        row[player_col].replace("*", "").replace("+", "").strip()
                    )
                    player_slug = slugify(player_name)
                    all_player_scores.setdefault(player_slug, []).append(
                        float(row[fpts_col])
                    )
                time.sleep(0.5)
            except Exception as e:
                log.error(
                    f"Failed to parse {pos.upper()} Week {week}.",
                    extra={"error": str(e)},
                )
    log.info(f"Finished scraping historical data for {len(all_player_scores)} players.")
    return all_player_scores
