"""Explore the Open-Meteo archive API: inspect fields/types and check
how many days behind 'today' the archive actually lags."""
import datetime as dt

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
PARIS = {"latitude": 48.8566, "longitude": 2.3522}


def inspect_recent_days(n=10):
    """Request the last n days for Paris and print what comes back."""
    today = dt.date.today()
    start = today - dt.timedelta(days=n)
    resp = requests.get(
        ARCHIVE_URL,
        params={
            **PARIS,
            "start_date": start.isoformat(),
            "end_date": today.isoformat(),
            "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation,cloud_cover",
            "timezone": "UTC",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    hourly = data["hourly"]
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    print(f"Requested {start} .. {today} ({n} days)")
    print(f"Got {len(times)} hourly timestamps, from {times[0]} to {times[-1]}")

    none_count = sum(1 for t in temps if t is None)
    print(f"temperature_2m: {none_count} None out of {len(temps)}")

    print("\nLast 6 hours returned:")
    for t, temp in zip(times[-6:], temps[-6:]):
        print(f"  {t}  temperature_2m={temp!r}")


if __name__ == "__main__":
    inspect_recent_days()
