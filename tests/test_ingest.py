"""Unit tests for the refuse-before-loading logic (step 3)."""
import pytest

from pipeline.ingest import _validate_or_refuse
from pipeline.schema import RAW_ECO2MIX


def test_valid_batch_does_not_exit():
    rows = [
        {
            "code_insee_region": "75",
            "date_heure": "2026-11-10T00:00:00+00:00",
            "consommation": 5000,
            "nucleaire": 4000,
            "eolien": 200,
            "solaire": 0,
            "hydraulique": 500,
        }
    ]
    _validate_or_refuse(rows, RAW_ECO2MIX, "eco2mix")  # must not raise


def test_bad_batch_exits_with_code_1():
    rows = [
        {
            "code_insee_region": "99",  # not a known region
            "date_heure": "2026-11-10T00:00:00+00:00",
            "consommation": 5000,
            "nucleaire": 4000,
            "eolien": 200,
            "solaire": 0,
            "hydraulique": 500,
        }
    ]
    with pytest.raises(SystemExit) as exc_info:
        _validate_or_refuse(rows, RAW_ECO2MIX, "eco2mix")
    assert exc_info.value.code == 1
