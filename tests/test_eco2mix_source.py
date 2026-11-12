"""Unit tests for the definitive/real-time dataset cutover logic (ADR 0002).

This is pure decision logic with no network call, so it's tested the TP1
way: a small hand-written case, a known expected answer.
"""
from pipeline.sources.eco2mix import (
    CUTOVER_DATE,
    DEFINITIVE_ID,
    REALTIME_ID,
    _normalize_backfill_row,
    _plan_fetches,
)


def test_range_entirely_before_cutover_uses_definitive_only():
    plan = _plan_fetches("2020-01-01", "2020-02-01")
    assert plan == [(DEFINITIVE_ID, "2020-01-01", "2020-02-01")]


def test_range_entirely_after_cutover_uses_realtime_only():
    plan = _plan_fetches("2026-09-01", "2026-09-02")
    assert plan == [(REALTIME_ID, "2026-09-01", "2026-09-02")]


def test_range_straddling_cutover_splits_across_both_datasets():
    plan = _plan_fetches("2026-08-20", "2026-09-10")
    assert plan == [
        (DEFINITIVE_ID, "2026-08-20", CUTOVER_DATE),
        (REALTIME_ID, CUTOVER_DATE, "2026-09-10"),
    ]


def test_range_ending_exactly_on_cutover_uses_definitive_only():
    # end_date is exclusive (see fetch_eco2mix_rows docstring), so a range
    # ending exactly on the cutover date never touches the real-time dataset.
    plan = _plan_fetches("2026-08-01", CUTOVER_DATE)
    assert plan == [(DEFINITIVE_ID, "2026-08-01", CUTOVER_DATE)]


def test_normalize_backfill_row_treats_empty_string_as_missing():
    assert _normalize_backfill_row({"eolien": ""})["eolien"] is None


def test_normalize_backfill_row_treats_dash_as_missing():
    # Found in real 2013 data: the CSV export uses a literal "-" for a
    # measurement that wasn't metered yet, distinct from an empty string.
    assert _normalize_backfill_row({"eolien": "-"})["eolien"] is None


def test_normalize_backfill_row_leaves_real_values_alone():
    row = _normalize_backfill_row({"eolien": "193", "code_insee_region": "75"})
    assert row == {"eolien": "193", "code_insee_region": "75"}
