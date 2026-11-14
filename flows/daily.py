"""The daily flow: ingest -> dbt build -> publish.

Run once a day (Automatic promise). Each task gets Prefect's own retries,
independent of pipeline/http_utils.py's lower-level HTTP retries (step 10)
-- that one retries a single flaky request; this one retries a whole task
if it still fails after that, with a longer delay, and the Prefect UI
records every attempt.

Targets prod.duckdb, not dev.duckdb: dev is the student's own interactive
work (ad-hoc dbt runs, query.py exploration), prod is what an orchestrated
run is supposed to own, so the two never race over the same file (see
CLAUDE.md section 7's note on DuckDB's single-writer constraint).

Run from the repo root:
    python -m flows.daily                      # one run, right now
    python -m flows.daily --serve               # register the daily 06:00 UTC schedule and keep running
"""
import argparse
import datetime as dt
import os
import shutil
import subprocess
import time

from prefect import flow, task
from prefect.logging import get_run_logger

from flows.alerts import discord_failure_hook
from flows.metrics import push_run_metrics
from pipeline.ingest import run_ingest

PROD_DUCKDB_PATH = os.environ.get("PROD_DUCKDB_PATH", "prod.duckdb")
SERVING_DUCKDB_PATH = os.environ.get("SERVING_DUCKDB_PATH", "serving.duckdb")

# The real-time dataset's freshest ~7 hours arrive with every measurement
# null, filled in later (ADR 0002 addendum) -- re-ingesting a trailing
# window every day, not just "yesterday to today", lets dlt's merge
# upsert the real values once they show up instead of leaving them
# quarantined forever. 2 days is comfortably more than the observed gap.
TRAILING_WINDOW_DAYS = 2


@task(retries=3, retry_delay_seconds=60)
def ingest_task(start_date: str, end_date: str) -> dict:
    logger = get_run_logger()
    logger.info("Ingesting %s to %s into %s", start_date, end_date, PROD_DUCKDB_PATH)
    counts = run_ingest(start_date, end_date, PROD_DUCKDB_PATH)
    logger.info("Ingested %s", counts)
    return counts


@task(retries=2, retry_delay_seconds=120)
def dbt_build_task() -> None:
    logger = get_run_logger()
    result = subprocess.run(
        ["dbt", "build", "--target", "prod"],
        check=False,
        capture_output=True,
        text=True,
    )
    logger.info(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)
        raise RuntimeError(f"dbt build --target prod failed (exit {result.returncode})")


@task
def publish_task() -> None:
    """Copy the freshly-built prod.duckdb to a separate serving file.

    The dashboard (step 14) will read SERVING_DUCKDB_PATH read-only, never
    prod.duckdb directly -- DuckDB only allows one read-write handle on a
    file at a time, so a dashboard holding prod.duckdb open would block
    tomorrow's dbt build. This is the write-audit-publish pattern CLAUDE.md
    section 7 describes: dbt build is the write+audit (its own tests are
    the audit gate -- dbt_build_task already failed the flow if any test
    failed), this copy is the publish.
    """
    logger = get_run_logger()
    shutil.copyfile(PROD_DUCKDB_PATH, SERVING_DUCKDB_PATH)
    logger.info("Published %s -> %s", PROD_DUCKDB_PATH, SERVING_DUCKDB_PATH)


@flow(name="daily-energy-platform-run", on_failure=[discord_failure_hook])
def daily_flow(start_date: str | None = None, end_date: str | None = None) -> None:
    if start_date is None or end_date is None:
        today = dt.date.today()
        start_date = (today - dt.timedelta(days=TRAILING_WINDOW_DAYS)).isoformat()
        end_date = (today + dt.timedelta(days=1)).isoformat()  # exclusive bound covers today

    started_at = time.monotonic()
    success = False
    counts = {"eco2mix_rows": 0, "weather_rows": 0}
    try:
        counts = ingest_task(start_date, end_date)
        dbt_build_task()
        publish_task()
        # No dashboard exists yet (step 14) -- a "refresh" task joins here
        # once one does; which API call that means depends entirely on
        # which tool (Metabase vs. Evidence) gets picked, so it's
        # deliberately not stubbed out blind. See ADR 0006.
        success = True
    finally:
        # Push metrics on success AND failure (step 13, ADR 0007) -- a
        # failed run should show up as freshness/reject-rate going stale
        # in Grafana, a separate, data-level signal from "the run crashed"
        # (the Discord on_failure hook above already covers that one).
        push_run_metrics(
            SERVING_DUCKDB_PATH,
            duration_seconds=time.monotonic() - started_at,
            eco2mix_rows=counts["eco2mix_rows"],
            weather_rows=counts["weather_rows"],
            success=success,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="register the daily schedule and keep running")
    parser.add_argument("--start-date", help="override the trailing window, inclusive YYYY-MM-DD")
    parser.add_argument("--end-date", help="override the trailing window, exclusive YYYY-MM-DD")
    args = parser.parse_args()

    if args.serve:
        daily_flow.serve(name="daily-energy-platform", cron="0 6 * * *")
    else:
        daily_flow(start_date=args.start_date, end_date=args.end_date)


if __name__ == "__main__":
    main()
