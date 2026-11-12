"""Pandera schemas that judge a whole ingestion batch before it is loaded.

Pandera does not replace dbt's row-by-row rules (step 5): a single negative
consommation still goes to quarantine there, not here. This is a coarser
question: is the *whole batch* usable at all, or did the API hand us
something broken enough that loading it would be worse than refusing it?
"""
import csv
from pathlib import Path

import pandera.pandas as pa

REGIONS_CSV = Path(__file__).resolve().parent.parent / "seeds" / "regions.csv"


def _known_region_codes():
    with open(REGIONS_CSV, newline="", encoding="utf-8") as f:
        return [row["code_insee_region"] for row in csv.DictReader(f)]


def _mostly_between(low, high, min_fraction=0.95):
    """Build a Check: at least min_fraction of the column's values are in [low, high]."""

    def check(series):
        return series.between(low, high).mean() >= min_fraction

    pct = int((1 - min_fraction) * 100)
    return pa.Check(check, error=f"more than {pct}% of the values are outside [{low}, {high}]")


# eco2mix: the definitive and real-time datasets have genuinely different
# optional columns (ADR 0002) -- eolien_terrestre/offshore only exist in one,
# column_30/column_68 are each dataset's own junk column. strict=False lets
# those pass through unflagged. It's the columns listed below -- the ones
# staging (step 4) actually depends on -- that must be present and plausible
# in every batch, no matter which of the two datasets it came from.
RAW_ECO2MIX = pa.DataFrameSchema(
    {
        "code_insee_region": pa.Column(str, pa.Check.isin(_known_region_codes()), nullable=False),
        "date_heure": pa.Column(str, nullable=False),
        "consommation": pa.Column(float, _mostly_between(0, 20000), nullable=True),
        "nucleaire": pa.Column(float, _mostly_between(0, 20000), nullable=True),
        "eolien": pa.Column(float, _mostly_between(0, 20000), nullable=True),
        "solaire": pa.Column(float, _mostly_between(0, 20000), nullable=True),
        "hydraulique": pa.Column(float, _mostly_between(0, 20000), nullable=True),
    },
    strict=False,
    coerce=True,
)

# weather: one source, one stable schema -- strict=True so a field Open-Meteo
# renames or drops is refused right away, not discovered weeks later as a
# silently-missing column.
RAW_WEATHER = pa.DataFrameSchema(
    {
        "code_insee_region": pa.Column(str, nullable=False),
        "region_name": pa.Column(str, nullable=False),
        "time": pa.Column(str, nullable=False),
        "temperature_2m": pa.Column(float, _mostly_between(-30, 45), nullable=True),
        "wind_speed_10m": pa.Column(float, _mostly_between(0, 150), nullable=True),
        "shortwave_radiation": pa.Column(float, _mostly_between(0, 1200), nullable=True),
        "cloud_cover": pa.Column(float, _mostly_between(0, 100), nullable=True),
    },
    strict=True,
    coerce=True,
)
