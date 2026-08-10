# Path: ffbPlayerDraftingApp/backend/cli.py

"""Command-Line Interface for the Fantasy Football Backend."""

import json
from pathlib import Path
import sys

import click

# The import paths are now relative to the 'backend' directory, which is
# the root of our application when running with `python -m backend.cli`.
from backend.logging_config import log
from backend import history_store
from backend.data_sources.source_diagnostics import run_source_diagnostics
from backend.pipelines.clean import run_clean
from backend.pipelines.enrich import run_enrich
from backend.pipelines.ingest import run_ingest
from backend.pipelines.stats import run_stats
from backend.pipelines.vor import run_vor
from backend.refresh_data import refresh_all


# The @click.group decorator makes `cli` a parent command that can have subcommands.
@click.group()
@click.option(
    "--date",
    default=None,
    help="The date for the run in 'YYYY-MM-DD' format. Defaults to today.",
)
@click.pass_context
def cli(ctx, date):
    """A CLI for the fantasy football data pipeline."""
    # The context object (ctx.obj) is a dictionary that we can use to pass
    # state (like the date) to subcommands.
    ctx.obj = {"date": date}


@cli.command()
@click.pass_context
def ingest(ctx):
    """Phase 1: Fetch raw player data from Sleeper API."""
    log.info("CLI: Running ingest phase.")
    try:
        run_ingest(date_str=ctx.obj["date"])
    except Exception:
        log.exception("CLI: Ingest phase failed.")
        sys.exit(1)  # Exit with a non-zero code to indicate failure


@cli.command()
@click.pass_context
def clean(ctx):
    """Phase 2: Filter players to keep only rostered and relevant ones."""
    log.info("CLI: Running clean phase.")
    try:
        run_clean(date_str=ctx.obj["date"])
    except Exception:
        log.exception("CLI: Clean phase failed.")
        sys.exit(1)


@cli.command()
@click.pass_context
def enrich(ctx):
    """Phase 3: Enrich players with ADP and projection data."""
    log.info("CLI: Running enrich phase.")
    try:
        run_enrich(date_str=ctx.obj["date"])
    except Exception:
        log.exception("CLI: Enrich phase failed.")
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Phase 4: Calculate the composite 'expected_ppg' score."""
    log.info("CLI: Running stats phase.")
    try:
        run_stats(date_str=ctx.obj["date"])
    except Exception:
        log.exception("CLI: Stats phase failed.")
        sys.exit(1)


@cli.command()
@click.pass_context
def vor(ctx):
    """Phase 5: Calculate VOR and produce the final ranked list."""
    log.info("CLI: Running VOR phase.")
    try:
        run_vor(date_str=ctx.obj["date"])
    except Exception:
        log.exception("CLI: VOR phase failed.")
        sys.exit(1)


@cli.command()
@click.pass_context
def all(ctx):
    """Run all pipeline phases in sequence: Ingest -> Clean -> Enrich -> Stats -> VOR."""
    log.info("CLI: Running all pipeline phases.")
    date = ctx.obj["date"]
    try:
        # log.info("--- Phase 1: Ingest ---")
        # run_ingest(date_str=date)

        log.info("--- Phase 2: Clean ---")
        run_clean(date_str=date)

        log.info("--- Phase 3: Enrich ---")
        run_enrich(date_str=date)

        log.info("--- Phase 4: Stats ---")
        run_stats(date_str=date)

        log.info("--- Phase 5: VOR ---")
        run_vor(date_str=date)

        log.info("CLI: All phases completed successfully.")

    except Exception:
        log.exception("CLI: The 'all' command failed during one of its phases.")
        sys.exit(1)



@cli.command("refresh-json")
@click.pass_context
def refresh_json(ctx):
    """Refresh all draft-ready public JSON files from current free sources."""
    log.info("CLI: Refreshing draft-ready public JSON files.")
    try:
        manifest = refresh_all(date_str=ctx.obj["date"])
        click.echo(json.dumps(manifest, indent=2))
    except Exception:
        log.exception("CLI: refresh-json failed.")
        sys.exit(1)

@cli.group()
def sources():
    """External source diagnostics before refreshing draft data."""


@sources.command("check")
@click.option("--scoring", default="HALF", type=click.Choice(["HALF", "PPR", "STD"]))
@click.option(
    "--output",
    "output_path",
    default="local/source_manifest.json",
    type=click.Path(path_type=str),
    help="Where to write the source-check manifest.",
)
def sources_check(scoring, output_path):
    """Check source URLs, tables, columns, and row counts."""
    manifest = run_source_diagnostics(scoring=scoring, output_path=Path(output_path))
    click.echo(json.dumps(manifest, indent=2))
    if not manifest["ok"]:
        sys.exit(1)

@cli.group()
@click.option(
    "--db",
    "db_path",
    default=None,
    type=click.Path(path_type=str),
    help="Local SQLite history DB. Defaults to local/draft_history.sqlite.",
)
@click.pass_context
def history(ctx, db_path):
    """Local-only draft history utilities."""
    resolved_db = (
        history_store.default_db_path(Path.cwd())
        if db_path is None
        else Path(db_path)
    )
    ctx.obj = {**ctx.obj, "db_path": resolved_db}


@history.command("init")
@click.pass_context
def history_init(ctx):
    """Create the local draft history database."""
    db_path = ctx.obj["db_path"]
    history_store.init_db(db_path)
    click.echo(f"Initialized {db_path}")


@history.command("template")
@click.argument("output_path", type=click.Path(path_type=str))
def history_template(output_path):
    """Write a manual draft-history CSV template."""
    path = Path(output_path)
    history_store.write_csv_template(path)
    click.echo(f"Wrote {path}")


@history.command("import-csv")
@click.argument("csv_path", type=click.Path(exists=True, path_type=str))
@click.option("--league", "league_key", required=True)
@click.option("--season", required=True, type=int)
@click.option("--platform", required=True)
@click.pass_context
def history_import_csv(ctx, csv_path, league_key, season, platform):
    """Import manual Yahoo/Sleeper/live draft history from CSV."""
    count = history_store.import_csv(
        ctx.obj["db_path"],
        Path(csv_path),
        league_key=league_key,
        season=season,
        platform=platform,
    )
    click.echo(f"Imported {count} picks")


@history.command("import-sleeper")
@click.option("--draft-id", required=True)
@click.option("--league", "league_key", required=True)
@click.option("--season", required=True, type=int)
@click.pass_context
def history_import_sleeper(ctx, draft_id, league_key, season):
    """Import public Sleeper draft picks by draft ID."""
    count = history_store.import_sleeper_draft(
        ctx.obj["db_path"], draft_id=draft_id, league_key=league_key, season=season
    )
    click.echo(f"Imported {count} Sleeper picks")


@history.command("export-json")
@click.argument("output_path", type=click.Path(path_type=str))
@click.pass_context
def history_export_json(ctx, output_path):
    """Export local draft history to a portable JSON backup."""
    count = history_store.export_json(ctx.obj["db_path"], Path(output_path))
    click.echo(f"Exported {count} picks")


@history.command("tendencies")
@click.pass_context
def history_tendencies(ctx):
    """Print simple manager tendency summaries from local history."""
    rows = history_store.manager_tendencies(ctx.obj["db_path"])
    click.echo(json.dumps(rows, indent=2))


if __name__ == "__main__":
    cli()


