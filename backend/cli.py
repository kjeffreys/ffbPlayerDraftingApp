# backend/backend/cli.py
"""
Command-Line Interface for the Fantasy Football Backend.

This module provides commands to run the data pipeline stages.
"""

import sys

import click

from logging_config import setup_logging
from pipelines.clean import run_clean
from pipelines.enrich import run_enrich
from pipelines.ingest import run_ingest
from pipelines.stats import run_stats
from pipelines.vor import run_vor

log = setup_logging(__name__)


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
    # state to subcommands. Here, we store the date.
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
        log.info("--- Phase 1: Ingest ---")
        run_ingest(date_str=date)

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
