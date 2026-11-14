"""Unit tests for the pure read-side of flows/metrics.py (step 13).

Builds a tiny throwaway DuckDB file with the handful of tables/columns
these functions actually read -- no live warehouse, no Pushgateway --
same TP1 style as the rest of the project: a small hand-written table, a
known expected answer.
"""
import datetime as dt

import duckdb

from flows.metrics import compute_freshness_hours, compute_reject_rate


def test_freshness_hours_on_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.duckdb"
    assert compute_freshness_hours(str(missing)) == float("inf")


def test_freshness_hours_reads_max_date_heure(tmp_path):
    db_path = tmp_path / "warehouse.duckdb"
    five_hours_ago = dt.datetime.now(dt.UTC) - dt.timedelta(hours=5)
    with duckdb.connect(str(db_path)) as conn:
        conn.execute("create table fct_energy_production (date_heure timestamp)")
        conn.execute("insert into fct_energy_production values (?)", [five_hours_ago.replace(tzinfo=None)])

    freshness = compute_freshness_hours(str(db_path))
    assert 4.9 < freshness < 5.1


def test_freshness_hours_on_empty_table(tmp_path):
    db_path = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(db_path)) as conn:
        conn.execute("create table fct_energy_production (date_heure timestamp)")

    assert compute_freshness_hours(str(db_path)) == float("inf")


def test_reject_rate_on_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.duckdb"
    assert compute_reject_rate(str(missing)) == (0, 0, 0.0)


def test_reject_rate_computes_fraction(tmp_path):
    db_path = tmp_path / "warehouse.duckdb"
    with duckdb.connect(str(db_path)) as conn:
        conn.execute("create table stg_eco2mix_regional (id integer)")
        conn.execute("insert into stg_eco2mix_regional select * from range(10)")
        conn.execute("create table eco2mix_rejected (id integer)")
        conn.execute("insert into eco2mix_rejected select * from range(2)")

    rejected, total, rate = compute_reject_rate(str(db_path))
    assert (rejected, total) == (2, 10)
    assert rate == 0.2
