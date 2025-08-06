# Path: ffbPlayerDraftingApp/backend/pipelines/enrich.py

import datetime, pandas as pd
from thefuzz import process
from backend.data_sources import fantasypros, yahoo
from backend.logging_config import log
from backend.settings import settings
from backend.storage.file_store import load_json, save_json
from backend.utils import slugify


def run_enrich(date_str: str | None = None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    log.info("Starting enrich pipeline.", extra={"date": date_str})

    input_path = settings.DATA_DIR / date_str / "roster_players.json"
    output_path = settings.DATA_DIR / date_str / "players_enriched.json"
    try:
        df = pd.DataFrame(load_json(input_path))
        df["slug"] = [
            slugify(f"{f} {l}") for f, l in zip(df["first_name"], df["last_name"])
        ]

        adp_map = fantasypros.fetch_adp()
        proj_map = yahoo.fetch_projected_points()

        # --- ROBUST FUZZY MATCHING ---
        canonical_slugs = df["slug"].dropna().unique().tolist()

        def create_fuzzy_map(data_map, choices):
            return {
                match[0]: data_map[slug]
                for slug, match in {
                    slug: process.extractOne(slug, choices, score_cutoff=85)
                    for slug in data_map.keys()
                }.items()
                if match
            }

        df["adp"] = df["slug"].map(create_fuzzy_map(adp_map, canonical_slugs))
        df["projected_points"] = df["slug"].map(
            create_fuzzy_map(proj_map, canonical_slugs)
        )

        # --- THE DEFINITIVE bye_week FIX ---
        if "fantasy_data_tms_bye_week" in df.columns:
            df.rename(columns={"fantasy_data_tms_bye_week": "bye_week"}, inplace=True)

        save_json(output_path, df.to_dict(orient="records"))
        log.info("Enrich pipeline completed successfully.")
    except Exception as e:
        log.exception("Enrich pipeline failed.", extra={"error": str(e)})
        raise
