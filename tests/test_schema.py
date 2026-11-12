"""Unit tests for the Pandera schemas (step 3): a small hand-written batch,
a known expected answer -- same shape as TP1's tests/test_pipeline.py.
"""
import pandas as pd
import pandera.errors
import pytest

from pipeline.schema import RAW_ECO2MIX, RAW_WEATHER


def make_eco2mix_rows(rows):
    """Build a small eco2mix batch. Each row only gives the columns it wants to change."""
    default = {
        "code_insee_region": "75",
        "date_heure": "2026-11-10T00:00:00+00:00",
        "consommation": 5000,
        "nucleaire": 4000,
        "eolien": 200,
        "solaire": 0,
        "hydraulique": 500,
    }
    return pd.DataFrame([{**default, **row} for row in rows])


def test_valid_batch_passes():
    df = make_eco2mix_rows([{}, {"code_insee_region": "11"}])
    RAW_ECO2MIX.validate(df, lazy=True)  # raises on failure, so no assert needed


def test_mixed_string_and_int_eolien_coerces_to_float():
    # The exact step-1 finding: eolien is a string in the definitive dataset,
    # an int in the real-time one. A batch mixing both must still validate.
    df = make_eco2mix_rows([{"eolien": "193"}, {"eolien": 207}])
    validated = RAW_ECO2MIX.validate(df, lazy=True)
    assert validated["eolien"].dtype.name == "float64"


def test_unknown_region_is_refused():
    df = make_eco2mix_rows([{"code_insee_region": "99"}])
    with pytest.raises(pandera.errors.SchemaErrors) as exc_info:
        RAW_ECO2MIX.validate(df, lazy=True)
    failure_cases = exc_info.value.failure_cases
    assert "code_insee_region" in failure_cases["column"].values


def test_implausible_consumption_is_refused():
    # 2 implausible rows out of 2 -- "mostly plausible" (>= 95%) cannot pass.
    df = make_eco2mix_rows([{"consommation": -500}, {"consommation": 999999}])
    with pytest.raises(pandera.errors.SchemaErrors):
        RAW_ECO2MIX.validate(df, lazy=True)


def make_weather_rows(rows):
    default = {
        "code_insee_region": "75",
        "region_name": "Nouvelle-Aquitaine",
        "time": "2026-11-10T00:00",
        "temperature_2m": 10.0,
        "wind_speed_10m": 5.0,
        "shortwave_radiation": 0.0,
        "cloud_cover": 90,
    }
    return pd.DataFrame([{**default, **row} for row in rows])


def test_weather_valid_batch_passes():
    df = make_weather_rows([{}, {"code_insee_region": "11"}])
    RAW_WEATHER.validate(df, lazy=True)


def test_weather_extra_column_is_refused():
    # strict=True: an undeclared column means Open-Meteo's shape changed.
    df = make_weather_rows([{}])
    df["surprise_field"] = "???"
    with pytest.raises(pandera.errors.SchemaErrors):
        RAW_WEATHER.validate(df, lazy=True)
