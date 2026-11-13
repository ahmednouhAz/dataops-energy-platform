"""CLI entrypoint: fetch, validate with Pandera, then load into the raw schema.

A batch that fails validation is refused entirely -- nothing from it is
loaded, exit code 1 -- same philosophy as TP4's load_raw.py. This judges the
whole batch; dbt's row-by-row rules (step 5) still apply afterwards.

Run from the repo root:
    python -m pipeline.ingest --start-date 2026-11-10 --end-date 2026-11-12
"""
import argparse
import datetime as dt
import os
import sys

import dlt
import pandas as pd
import pandera.errors

from pipeline.schema import RAW_ECO2MIX, RAW_WEATHER
from pipeline.sources import eco2mix, weather

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dev.duckdb")


def _validate_or_refuse(rows: list[dict], schema, label: str) -> None:
    """Exit 1 and load nothing if the batch doesn't match the expected schema."""
    df = pd.DataFrame(rows)
    try:
        schema.validate(df, lazy=True)
    except pandera.errors.SchemaErrors as error:
        print(f"REFUSED: {label} batch does not match the expected schema")
        print(error.failure_cases[["column", "check", "failure_case"]].to_string(index=False))
        sys.exit(1)


def run_ingest(start_date: str, end_date: str, duckdb_path: str) -> dict:
    """Fetch, validate, and merge-load both sources for [start_date, end_date)
    -- end_date exclusive, for *both* sources, from the caller's point of
    view (e.g. "today" means pass tomorrow's date to get data through today).

    eco2mix's own API is exclusive on end_date already; weather's archive
    API is inclusive, and rejects a date beyond today outright (ADR 0002).
    Subtracting one day for the weather call is how pipeline/backfill.py's
    _load_weather_chunk already reconciles the same two conventions for the
    same two sources (step 10) -- found missing here only once flows/daily.py
    (step 12) tried to default end_date to "tomorrow" for an automated run:
    the CLI had always been called by hand with a value that happened to
    avoid the mismatch, so this bug was latent until something called it
    with "today" for real.

    Pulled out of main() in step 12 so flows/daily.py's Prefect task can call
    this directly -- no subprocess, no re-parsing argv -- and get back the
    row counts as data instead of scraping stdout. main() below is now a
    thin CLI wrapper around the same function.
    """
    eco2mix_rows = eco2mix.fetch_eco2mix_rows(start_date, end_date)
    print(f"Fetched {len(eco2mix_rows)} eco2mix rows")
    if eco2mix_rows:
        _validate_or_refuse(eco2mix_rows, RAW_ECO2MIX, "eco2mix")

    weather_end_date = (dt.date.fromisoformat(end_date) - dt.timedelta(days=1)).isoformat()
    weather_rows = weather.fetch_weather_rows(start_date, weather_end_date)
    print(f"Fetched {len(weather_rows)} weather rows")
    if weather_rows:
        _validate_or_refuse(weather_rows, RAW_WEATHER, "weather")

    pipeline = dlt.pipeline(
        pipeline_name="energy_platform",
        destination=dlt.destinations.duckdb(duckdb_path),
        dataset_name="raw",
    )

    if eco2mix_rows:
        eco2mix_resource = dlt.resource(
            eco2mix_rows,
            name=eco2mix.RESOURCE_NAME,
            write_disposition="merge",
            primary_key=eco2mix.PRIMARY_KEY,
            columns=eco2mix.TEXT_COLUMN_HINTS,
        )
        print(pipeline.run(eco2mix_resource))

    if weather_rows:
        weather_resource = dlt.resource(
            weather_rows,
            name=weather.RESOURCE_NAME,
            write_disposition="merge",
            primary_key=weather.PRIMARY_KEY,
        )
        print(pipeline.run(weather_resource))

    return {"eco2mix_rows": len(eco2mix_rows), "weather_rows": len(weather_rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True, help="inclusive, YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="exclusive for both sources, YYYY-MM-DD")
    args = parser.parse_args()
    run_ingest(args.start_date, args.end_date, DUCKDB_PATH)


if __name__ == "__main__":
    main()
