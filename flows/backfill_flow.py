"""Prefect-wrapped backfill: the same year-chunk logic pipeline/backfill.py
already proved correct in step 10 (ADR 0004), now with per-chunk Prefect
retries and progress visible in the Prefect UI instead of print()
statements -- an orchestration layer over already-tested code, not a
second implementation of the same thing to keep in sync by hand.

pipeline/http_utils.py's get_with_retries already retries one flaky HTTP
call a few times (step 10); this adds a second, coarser layer -- if a
whole chunk still fails after that (e.g. a longer outage), Prefect retries
the chunk itself, with a longer delay, and records every attempt.

Run from the repo root:
    python -m flows.backfill_flow --start-date 2013-01-01 --end-date 2026-08-31
"""
import argparse
import os

import dlt
from prefect import flow, task
from prefect.logging import get_run_logger

from flows.alerts import discord_failure_hook
from pipeline.backfill import (
    DEFAULT_START,
    _load_eco2mix_chunk,
    _load_weather_chunk,
    _year_chunks,
)
from pipeline.sources import eco2mix

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dev.duckdb")


@task(retries=3, retry_delay_seconds=60)
def backfill_chunk_task(pipeline, chunk_start: str, chunk_end: str) -> None:
    logger = get_run_logger()
    logger.info("Backfilling %s .. %s", chunk_start, chunk_end)
    _load_eco2mix_chunk(pipeline, chunk_start, chunk_end)
    _load_weather_chunk(pipeline, chunk_start, chunk_end)
    logger.info("Chunk %s .. %s done", chunk_start, chunk_end)


@flow(name="backfill-energy-platform", on_failure=[discord_failure_hook])
def backfill_flow(start_date: str = DEFAULT_START, end_date: str = eco2mix.CUTOVER_DATE) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="energy_platform",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name="raw",
    )
    for chunk_start, chunk_end in _year_chunks(start_date, end_date):
        backfill_chunk_task(pipeline, chunk_start, chunk_end)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default=DEFAULT_START)
    parser.add_argument("--end-date", default=eco2mix.CUTOVER_DATE)
    args = parser.parse_args()
    backfill_flow(start_date=args.start_date, end_date=args.end_date)


if __name__ == "__main__":
    main()
