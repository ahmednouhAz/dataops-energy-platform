"""Build the DVC-tracked reference dataset: one fixed week of real data from
both sources, saved as CSV under data/reference/.

Deliberately a FIXED historical date range, not "the last N days" -- a
reference dataset has to return the exact same thing every time it's
rebuilt, which a sliding window never would. 2026-09-01..09-07 is safely
past the real-time dataset's freshest-hours null gap (ADR 0002 addendum),
so every value in it is already final.

This is NOT the tiny CI sample (tests/fixtures/*.csv, kept in plain Git per
TP4: small and stable) and NOT the full historical backfill (step 10, lives
only in the warehouse, never saved as a file). It's a mid-sized, stable
slice for local testing and for rehearsing the backfill mechanics before
doing it for real.

Run from the repo root:
    python -m scripts.build_reference_dataset
"""
import csv
from pathlib import Path

from pipeline.sources.eco2mix import fetch_eco2mix_rows
from pipeline.sources.weather import fetch_weather_rows

START_DATE = "2026-09-01"
ECO2MIX_END_DATE = "2026-09-08"  # exclusive -> Sep 1-7
WEATHER_END_DATE = "2026-09-07"  # inclusive -> Sep 1-7

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"


def _write_csv(rows, path):
    if not rows:
        raise ValueError(f"No rows fetched for {path}")
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    eco2mix_rows = fetch_eco2mix_rows(START_DATE, ECO2MIX_END_DATE)
    _write_csv(eco2mix_rows, OUT_DIR / "eco2mix_regional.csv")

    weather_rows = fetch_weather_rows(START_DATE, WEATHER_END_DATE)
    _write_csv(weather_rows, OUT_DIR / "weather_hourly.csv")


if __name__ == "__main__":
    main()
