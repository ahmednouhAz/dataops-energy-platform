"""Run the CI fixtures past Pandera, the same gate pipeline/ingest.py uses
for a real batch -- refuses (exit 1) and prints nothing is loaded if either
fixture doesn't pass. Separate from tests/load_fixtures.py on purpose: this
is the quality gate, that one is "load it because it already passed".

Run from the repo root:
    python -m tests.validate_fixtures
"""
import pandas as pd

from pipeline.ingest import _validate_or_refuse
from pipeline.schema import RAW_ECO2MIX, RAW_WEATHER


def main():
    eco2mix_rows = pd.read_csv("tests/fixtures/eco2mix_sample.csv").to_dict("records")
    _validate_or_refuse(eco2mix_rows, RAW_ECO2MIX, "eco2mix")
    print(f"eco2mix fixture: {len(eco2mix_rows)} rows, valid")

    weather_rows = pd.read_csv("tests/fixtures/weather_sample.csv").to_dict("records")
    _validate_or_refuse(weather_rows, RAW_WEATHER, "weather")
    print(f"weather fixture: {len(weather_rows)} rows, valid")


if __name__ == "__main__":
    main()
