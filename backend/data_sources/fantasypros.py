"""
Get ADP from fantasypros
Respects ppr, half-ppr, and standard scoring
Also offers ADP from yahoo, sleeper, espn, and other sources
"""

# Path: ffbPlayerDraftingApp/backend/data_sources/fantasypros.py
import io, pandas as pd, requests
from backend.logging_config import log
from backend.settings import settings
from backend.utils import slugify


def fetch_adp() -> dict[str, float]:
    url = settings.FANTASYPROS_ADP_URL
    log.info("Fetching ADP data from FantasyPros.", extra={"url": url})
    try:
        headers = {"User-Agent": "Mozilla/5.0..."}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text), attrs={"id": "data"})
        if not tables:
            raise ValueError("ADP table not found.")
        df = tables[0]

        # --- DEFENSIVE CODING ---
        player_col = "Player Team (Bye)"
        adp_col = "AVG"
        if player_col not in df.columns or adp_col not in df.columns:
            log.error(
                f"Required ADP columns not found. Discovered: {df.columns.tolist()}"
            )
            return {}

        adp_map = {}
        for _, row in df.iterrows():
            name_parts = row[player_col].split()
            if len(name_parts) > 2:
                player_name = " ".join(name_parts[:-2])
            else:
                player_name = name_parts[0] if name_parts else ""
            if player_name:
                adp_map[slugify(player_name)] = float(row[adp_col])
        log.info("Successfully parsed ADP data.", extra={"player_count": len(adp_map)})
        return adp_map
    except Exception as e:
        log.exception("Failed to fetch or parse ADP data.", extra={"error": str(e)})
        raise
