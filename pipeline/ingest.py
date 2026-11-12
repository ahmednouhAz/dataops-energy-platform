"""CLI entrypoint: load both sources into the warehouse's raw schema.

Run from the repo root:
    python -m pipeline.ingest --start-date 2026-11-10 --end-date 2026-11-12
"""
import argparse
import os

import dlt

from pipeline.sources.eco2mix import eco2mix_source
from pipeline.sources.weather import weather_source

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dev.duckdb")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True, help="inclusive, YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="exclusive for eco2mix, inclusive for weather, YYYY-MM-DD")
    args = parser.parse_args()

    pipeline = dlt.pipeline(
        pipeline_name="energy_platform",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name="raw",
    )

    eco2mix_info = pipeline.run(eco2mix_source(args.start_date, args.end_date))
    print(eco2mix_info)

    weather_info = pipeline.run(weather_source(args.start_date, args.end_date))
    print(weather_info)


if __name__ == "__main__":
    main()
