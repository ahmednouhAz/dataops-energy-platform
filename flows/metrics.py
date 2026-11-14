"""Push per-run observability metrics to Prometheus's Pushgateway.

A batch job can't be *scraped* the normal Prometheus way -- it isn't a
long-running HTTP server with a /metrics endpoint, it runs for a few
seconds once a day. Pushgateway exists exactly for this: the job pushes
its own numbers once when it finishes, and Prometheus scrapes the
gateway on its own schedule afterward, same as it would scrape anything
else.

Freshness and reject-rate are read from SERVING_DUCKDB_PATH (the
published copy, not prod.duckdb) on purpose: this is what step 11/12
already built the write-audit-publish split for -- observability reads
the same file the dashboard (step 14) will, never the file dbt is
actively writing to.

Metrics are pushed on both success AND failure (see flows/daily.py's
try/finally) -- a failed run should make the freshness metric visibly
stop improving, which is a *separate* signal from "the run crashed"
(Prefect's own on_failure hook, flows/alerts.py already covers that one).
That's why this module never raises: a Pushgateway outage must not mask
or replace the real pipeline failure it's trying to report on.
"""
import datetime as dt
import os

import duckdb
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

PUSHGATEWAY_URL = os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091")
JOB_NAME = "energy_platform_daily"

# dbt-duckdb names the database after the *target*, not the file path --
# `dbt build --target prod` compiles every cross-schema reference inside a
# view (e.g. stg_eco2mix_regional's source() call) as `prod.raw....`. A
# raw file copy (publish_task) carries that compiled SQL as-is, so a plain
# duckdb.connect() on the copy can't resolve it: this connection has no
# catalog literally named "prod" unless we attach one ourselves. Found by
# hitting `Binder Error: Catalog "prod" does not exist!` on exactly the
# views (not the tables) the first time this ran for real.
_PROD_CATALOG = "prod"


def _connect_as_prod(duckdb_path: str):
    conn = duckdb.connect(":memory:")
    conn.execute(f"attach '{duckdb_path}' as {_PROD_CATALOG} (read_only)")
    conn.execute(f"use {_PROD_CATALOG}")
    return conn


def compute_freshness_hours(duckdb_path: str) -> float:
    """Hours between now and the most recent timestamp in fct_energy_production.

    inf if the file/table is empty or doesn't exist yet -- "infinitely
    stale" is the correct reading for "we have never successfully
    published data", not 0 and not an error. DuckDB can't attach a missing
    file read-only (it can't create it), so that case is checked first.
    """
    if not os.path.exists(duckdb_path):
        return float("inf")
    with _connect_as_prod(duckdb_path) as conn:
        tables = {row[0] for row in conn.execute("show tables").fetchall()}
        if "fct_energy_production" not in tables:
            return float("inf")
        max_date_heure = conn.execute("select max(date_heure) from fct_energy_production").fetchone()[0]
    if max_date_heure is None:
        return float("inf")
    if max_date_heure.tzinfo is None:
        max_date_heure = max_date_heure.replace(tzinfo=dt.UTC)
    now = dt.datetime.now(dt.UTC)
    return (now - max_date_heure).total_seconds() / 3600


def compute_reject_rate(duckdb_path: str) -> tuple[int, int, float]:
    """(rejected_rows, total_staged_rows, reject_rate) from the published warehouse.

    This is the whole dataset's current reject rate, not just today's
    batch -- the same number int_eco2mix_checked's own
    assert_reject_rate_below_20_percent singular test already guards in
    dbt (step 6); Grafana/Prometheus just makes it watchable over time
    instead of a pass/fail at build time only.
    """
    if not os.path.exists(duckdb_path):
        return 0, 0, 0.0
    with _connect_as_prod(duckdb_path) as conn:
        tables = {row[0] for row in conn.execute("show tables").fetchall()}
        if "eco2mix_rejected" not in tables or "stg_eco2mix_regional" not in tables:
            return 0, 0, 0.0
        rejected = conn.execute("select count(*) from eco2mix_rejected").fetchone()[0]
        total = conn.execute("select count(*) from stg_eco2mix_regional").fetchone()[0]
    rate = rejected / total if total else 0.0
    return rejected, total, rate


def push_run_metrics(
    duckdb_path: str,
    duration_seconds: float,
    eco2mix_rows: int,
    weather_rows: int,
    success: bool,
) -> None:
    """Compute and push this run's metrics. Never raises -- logged instead,
    so a Pushgateway/network problem can't hide a real pipeline failure
    behind a second, unrelated exception."""
    try:
        rejected, _total, reject_rate = compute_reject_rate(duckdb_path)
        freshness_hours = compute_freshness_hours(duckdb_path)

        registry = CollectorRegistry()
        Gauge(
            "energy_platform_run_duration_seconds",
            "Wall-clock duration of the last daily flow run",
            registry=registry,
        ).set(duration_seconds)
        # One Gauge object, two label values -- creating a second Gauge
        # with the same metric name (even with different .labels() calls)
        # registers the name twice and raises "Duplicated timeseries in
        # CollectorRegistry", found by actually pushing a real run's
        # metrics rather than assuming the two-call pattern was fine.
        rows_loaded = Gauge(
            "energy_platform_rows_loaded",
            "Rows fetched by the last run, per source",
            ["source"],
            registry=registry,
        )
        rows_loaded.labels(source="eco2mix").set(eco2mix_rows)
        rows_loaded.labels(source="weather").set(weather_rows)
        Gauge(
            "energy_platform_rows_rejected_total",
            "Total rows currently quarantined in eco2mix_rejected",
            registry=registry,
        ).set(rejected)
        Gauge(
            "energy_platform_reject_rate",
            "rejected / total staged rows, current warehouse state",
            registry=registry,
        ).set(reject_rate)
        Gauge(
            "energy_platform_freshness_hours",
            "Hours between now and the newest row in fct_energy_production",
            registry=registry,
        ).set(freshness_hours)
        Gauge(
            "energy_platform_run_success",
            "1 if the last daily flow run completed without error, else 0",
            registry=registry,
        ).set(1 if success else 0)

        push_to_gateway(PUSHGATEWAY_URL, job=JOB_NAME, registry=registry)
    except Exception as error:  # noqa: BLE001 -- observability must never crash the pipeline it's observing
        print(f"WARNING: failed to push metrics to {PUSHGATEWAY_URL}: {error}")
