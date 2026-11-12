"""Backfill eco2mix + weather history, one calendar year at a time.

Uses the bulk /exports endpoint for eco2mix (pipeline/sources/eco2mix.py's
fetch_definitive_backfill_rows), not the paginated /records endpoint
ordinary daily ingestion uses -- /records caps at 100 rows/page, which
would mean tens of thousands of requests for multi-year history.

Chunked by year, not one giant request, so a failure partway through
doesn't lose already-loaded years and so progress is visible while it
runs. Idempotency comes from an explicit delete-then-append per chunk
(_delete_existing_chunk), not dlt's own write_disposition="merge" --
merge re-scans the whole destination table on every load, which made this
get slower every year as the table grew (see ADR 0004). Day-to-day
ingestion (pipeline/ingest.py) stays on merge: its batches are small enough
that this never mattered there.

Run from the repo root:
    python -m pipeline.backfill --start-date 2013-01-01 --end-date 2026-08-31
"""
import argparse
import datetime as dt
import os

import dlt

from pipeline.ingest import _validate_or_refuse
from pipeline.schema import RAW_ECO2MIX, RAW_WEATHER
from pipeline.sources import eco2mix, weather

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dev.duckdb")
DEFAULT_START = "2013-01-01"  # earliest full year; the API's actual floor is
# 2012-12-31, one day earlier -- left out to keep chunk boundaries on
# calendar years, a negligible loss of a single day of history.


def _year_chunks(start_date: str, end_date: str):
    """Yield (chunk_start, chunk_end) covering [start_date, end_date), one
    calendar year per chunk, both dates exclusive-end (eco2mix convention).
    """
    start = dt.date.fromisoformat(start_date)
    end = dt.date.fromisoformat(end_date)
    year = start.year
    while True:
        chunk_start = max(start, dt.date(year, 1, 1))
        chunk_end = min(end, dt.date(year + 1, 1, 1))
        if chunk_start >= end:
            break
        yield chunk_start.isoformat(), chunk_end.isoformat()
        year += 1


def _delete_existing_chunk(pipeline, table_name, time_column, chunk_start, chunk_end):
    """Delete any rows already in [chunk_start, chunk_end) before an append.

    Found empirically: dlt's write_disposition="merge" re-scans the whole
    destination table on every load to find matching keys, so it got
    *slower with every year* as the table grew (chunk 1 took 1m42s, chunk 10
    took 8m27s -- see ADR 0004). Each year's rows never overlap another
    year's, so there is nothing to merge in the first place; an explicit
    delete-then-append on the exact date range gives the same idempotency
    (re-running a chunk replaces it, not duplicates it) in roughly constant
    time per chunk instead of growing with the table.
    """
    with pipeline.sql_client() as client:
        tables = {
            row[0]
            for row in client.execute_sql(
                "select table_name from information_schema.tables where table_schema = 'raw'"
            )
        }
        if table_name not in tables:
            return
        client.execute_sql(
            f"delete from raw.{table_name} where {time_column} >= '{chunk_start}' and {time_column} < '{chunk_end}'"
        )


def _load_eco2mix_chunk(pipeline, chunk_start, chunk_end):
    _delete_existing_chunk(pipeline, eco2mix.RESOURCE_NAME, "date_heure", chunk_start, chunk_end)
    rows = eco2mix.fetch_definitive_backfill_rows(chunk_start, chunk_end)
    print(f"  eco2mix: fetched {len(rows)} rows")
    _validate_or_refuse(rows, RAW_ECO2MIX, f"eco2mix backfill {chunk_start}")
    resource = dlt.resource(
        rows,
        name=eco2mix.RESOURCE_NAME,
        write_disposition="append",
        columns=eco2mix.TEXT_COLUMN_HINTS,
    )
    pipeline.run(resource)
    print("  eco2mix: loaded")


def _load_weather_chunk(pipeline, chunk_start, chunk_end):
    # fetch_weather_rows' end_date is inclusive; chunk_end here is
    # exclusive (eco2mix convention), so step back one day to avoid
    # double-fetching the first hour of the next chunk.
    weather_end = (dt.date.fromisoformat(chunk_end) - dt.timedelta(days=1)).isoformat()
    _delete_existing_chunk(pipeline, weather.RESOURCE_NAME, "time", chunk_start, chunk_end)
    rows = weather.fetch_weather_rows(chunk_start, weather_end)
    print(f"  weather: fetched {len(rows)} rows")
    _validate_or_refuse(rows, RAW_WEATHER, f"weather backfill {chunk_start}")
    resource = dlt.resource(
        rows,
        name=weather.RESOURCE_NAME,
        write_disposition="append",
    )
    pipeline.run(resource)
    print("  weather: loaded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default=DEFAULT_START)
    parser.add_argument("--end-date", default=eco2mix.CUTOVER_DATE)
    args = parser.parse_args()

    pipeline = dlt.pipeline(
        pipeline_name="energy_platform",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name="raw",
    )

    for chunk_start, chunk_end in _year_chunks(args.start_date, args.end_date):
        print(f"--- {chunk_start} .. {chunk_end} ---")
        _load_eco2mix_chunk(pipeline, chunk_start, chunk_end)
        _load_weather_chunk(pipeline, chunk_start, chunk_end)

    print("Backfill done.")


if __name__ == "__main__":
    main()
