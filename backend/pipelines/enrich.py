# backend/pipelines/enrich.py (Corrected)
import datetime
import pandas as pd

# --- CHANGE: Import only the consolidated fantasypros module ---
from backend.data_sources import fantasypros
from backend.logging_config import log
from backend.settings import settings
from backend.storage.file_store import load_json, save_json
from backend.utils import slugify, create_hybrid_slug_map


def run_enrich(date_str: str | None = None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    log.info("Starting enrich pipeline.", extra={"date": date_str})

    data_dir = settings.DATA_DIR / date_str
    input_path = data_dir / "roster_players.json"
    output_path = data_dir / "players_enriched.json"

    try:
        players_data = load_json(input_path)
        df = pd.DataFrame(players_data)
        df["slug"] = [
            slugify(f"{f} {l}") for f, l in zip(df["first_name"], df["last_name"])
        ]

        # --- CHANGE: Fetch data using the new, reliable functions ---
        log.info("Fetching ADP and Projection data from consolidated source...")
        adp_bye_map = fantasypros.fetch_adp()

        # Call the new projections function, which returns a DataFrame
        projections_df = fantasypros.fetch_all_projections()

        # --- ADDED: Convert the projections DataFrame to the required dictionary format ---
        # The create_hybrid_slug_map function expects a dict: {slug: value}
        if not projections_df.empty:
            proj_map = projections_df.set_index("player_slug")[
                "projection_fpts"
            ].to_dict()
            log.info(
                f"Successfully converted projections DataFrame to dictionary with {len(proj_map)} entries."
            )
        else:
            log.warning(
                "Received empty projections DataFrame. Projections will be missing."
            )
            proj_map = {}

        # The rest of the logic remains the same as it now has the data in the expected format
        canonical_slugs = df["slug"].dropna().unique().tolist()
        mapped_adp_bye = create_hybrid_slug_map(adp_bye_map, canonical_slugs)
        mapped_proj = create_hybrid_slug_map(proj_map, canonical_slugs)

        df["adp"] = (
            df["slug"]
            .map(mapped_adp_bye)
            .apply(lambda x: x[0] if isinstance(x, tuple) else None)
        )
        df["bye_week"] = (
            df["slug"]
            .map(mapped_adp_bye)
            .apply(lambda x: x[1] if isinstance(x, tuple) else None)
        )
        df["projected_points"] = df["slug"].map(mapped_proj)

        if "fantasy_data_tms_bye_week" in df.columns:
            df = df.drop(columns=["fantasy_data_tms_bye_week"])

        # Log a sample of the enriched data for verification
        log.info("Enrichment complete. Logging sample of projected points:")
        # The corrected line:
        log.info(
            f"\n{df[['first_name', 'last_name', 'slug', 'projected_points']].head(10).to_string()}"
        )

        save_json(output_path, df.to_dict(orient="records"))
        log.info(
            "Enrich pipeline completed successfully. Saved to players_enriched.json"
        )

    except Exception as e:
        log.exception("Enrich pipeline failed.", extra={"error": str(e)})
        raise
