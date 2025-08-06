# Path: ffbPlayerDraftingApp/backend/data_sources/yahoo.py
import io, pandas as pd, requests
from backend.logging_config import log
from backend.settings import settings
from backend.utils import slugify


def get_projection_url() -> str:
    scoring = settings.league_config.scoring.lower()
    return (
        f"https://www.fantasypros.com/nfl/projections/all.php?scoring={scoring.upper()}"
    )


def fetch_projected_points() -> dict[str, float]:
    url = get_projection_url()
    log.info("Fetching projections from FantasyPros.", extra={"url": url})
    try:
        headers = {"User-Agent": "Mozilla/5.0..."}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text), attrs={"id": "data"})
        if not tables:
            raise ValueError("Projections table not found.")
        df = tables[0]

        # --- DEFENSIVE CODING ---
        player_col_tuple = ("Unnamed: 0_level_0", "Player")
        fpts_col_tuple = ("MISC", "FPTS")
        if player_col_tuple not in df.columns or fpts_col_tuple not in df.columns:
            log.error(
                f"Required projection columns not found. Discovered: {df.columns.values}"
            )
            return {}

        proj_map = {}
        for _, row in df.iterrows():
            name = row[player_col_tuple].replace("*", "").replace("+", "").strip()
            proj_map[slugify(name)] = float(row[fpts_col_tuple])
        log.info(
            "Successfully parsed projections.", extra={"player_count": len(proj_map)}
        )
        return proj_map
    except Exception as e:
        log.exception("Failed to fetch or parse projections.", extra={"error": str(e)})
        raise
