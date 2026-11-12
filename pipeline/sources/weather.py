"""dlt source for Open-Meteo hourly weather, one call per region.

Uses seeds/regions.csv (step 1) to know which lat/lon represents each of
the 12 mainland France regions.
"""
import csv
from pathlib import Path

import dlt
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_FIELDS = "temperature_2m,wind_speed_10m,shortwave_radiation,cloud_cover"
REGIONS_CSV = Path(__file__).resolve().parents[2] / "seeds" / "regions.csv"


def _load_regions():
    with open(REGIONS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fetch_region(region, start_date, end_date):
    """Call the archive API for one region and yield one row per hour."""
    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": region["latitude"],
            "longitude": region["longitude"],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": HOURLY_FIELDS,
            "timezone": "UTC",
        },
        timeout=30,
    )
    resp.raise_for_status()
    hourly = resp.json()["hourly"]
    times = hourly["time"]
    for i, t in enumerate(times):
        yield {
            "code_insee_region": region["code_insee_region"],
            "region_name": region["region_name"],
            "time": t,
            "temperature_2m": hourly["temperature_2m"][i],
            "wind_speed_10m": hourly["wind_speed_10m"][i],
            "shortwave_radiation": hourly["shortwave_radiation"][i],
            "cloud_cover": hourly["cloud_cover"][i],
        }


@dlt.resource(
    name="weather_hourly",
    write_disposition="merge",
    primary_key=("code_insee_region", "time"),
)
def weather_hourly(start_date: str, end_date: str):
    """Yield hourly weather rows for every region for [start_date, end_date]."""
    for region in _load_regions():
        yield from _fetch_region(region, start_date, end_date)


@dlt.source
def weather_source(start_date: str, end_date: str):
    return weather_hourly(start_date, end_date)
