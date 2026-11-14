"""Headless Metabase setup: admin user, the DuckDB connection, and the
3 business-question cards + dashboard (step 14, ADR 0008).

Metabase has no YAML-provisioning convention like Grafana's -- this
script does the same job by calling Metabase's own REST API, the exact
calls its own setup wizard makes under the hood (found by testing the
calls directly before writing this script, not by guessing the schema).
Idempotent: every step checks whether its target already exists before
creating it, so re-running `docker compose up` (which re-runs this
one-shot job) never duplicates the database, cards, or dashboard.

Run from the repo root (normally via docker-compose.yml's
metabase-setup service, which already waits for Metabase to be healthy):
    python scripts/setup_metabase.py
"""
import os
import sys
import time

import requests

METABASE_URL = os.environ.get("METABASE_URL", "http://localhost:3001")
ADMIN_EMAIL = os.environ.get("METABASE_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("METABASE_ADMIN_PASSWORD", "change-me-locally")

DATABASE_NAME = "Energy Platform"
# The dashboard reads the published copy, never prod.duckdb directly --
# same write-audit-publish split every other reader of the warehouse
# uses (CLAUDE.md section 7, ADR 0007). /data is the whole repo,
# read-only, mounted by docker-compose.yml's metabase service.
DUCKDB_PATH_IN_CONTAINER = "/data/serving.duckdb"

# One entry per business question (docs/business_questions.md). Reads
# only fct_energy_production, fct_consumption_weather, dim_region,
# dim_energy_source -- all marts, never raw/staging/intermediate models
# (the project's "dashboard reads only from marts" rule).
CARDS = [
    {
        "name": "Q1 - Renewable share by region and month",
        "query": """
            select
                r.region_name,
                date_trunc('month', f.date_heure) as month,
                sum(case when s.is_renewable then f.production_mw else 0 end)
                    / sum(f.production_mw) as renewable_share
            from fct_energy_production f
            join dim_region r on f.code_insee_region = r.code_insee_region
            join dim_energy_source s on f.energy_source = s.energy_source
            group by 1, 2
            order by 1, 2
        """,
        "display": "line",
    },
    {
        "name": "Q2 - Consumption rise per degree of cold, by region",
        "query": """
            select
                r.region_name,
                -regr_slope(c.consommation_mw_avg, c.temperature_c) as mw_increase_per_degree_of_cold
            from fct_consumption_weather c
            join dim_region r on c.code_insee_region = r.code_insee_region
            group by 1
            order by 2 desc
        """,
        "display": "bar",
    },
    {
        "name": "Q3 - Peak consumption hour and grid role, by region",
        "query": """
            with peaks as (
                select
                    code_insee_region, observed_hour, consommation_mw_avg, ech_physiques_mw_avg,
                    row_number() over (partition by code_insee_region order by consommation_mw_avg desc) as rn
                from fct_consumption_weather
            )
            select
                r.region_name,
                p.observed_hour as peak_hour,
                p.consommation_mw_avg as peak_consumption_mw,
                p.ech_physiques_mw_avg as exchange_at_peak_mw,
                case when p.ech_physiques_mw_avg < 0 then 'imports' else 'exports' end as grid_role_at_peak
            from peaks p
            join dim_region r on p.code_insee_region = r.code_insee_region
            where p.rn = 1
            order by p.consommation_mw_avg desc
        """,
        "display": "table",
    },
]


def _wait_for_metabase():
    """Metabase's own healthcheck already waits for /api/health, but the
    setup/session properties endpoints can lag a few seconds behind that."""
    for _ in range(30):
        try:
            if requests.get(f"{METABASE_URL}/api/health", timeout=5).status_code == 200:
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    sys.exit("Metabase never became ready")


def _get_or_create_session() -> str:
    """Return a session token, creating the admin user on first run."""
    properties = requests.get(f"{METABASE_URL}/api/session/properties", timeout=10).json()
    if not properties["has-user-setup"]:
        resp = requests.post(
            f"{METABASE_URL}/api/setup",
            json={
                "token": properties["setup-token"],
                "user": {
                    "first_name": "Admin",
                    "last_name": "User",
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD,
                },
                "prefs": {"site_name": "Energy Platform", "allow_tracking": False},
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    resp = requests.post(
        f"{METABASE_URL}/api/session",
        json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _get_or_create_database(session: str) -> int:
    headers = {"X-Metabase-Session": session}
    existing = requests.get(f"{METABASE_URL}/api/database", headers=headers, timeout=10).json()
    for db in existing["data"]:
        if db["name"] == DATABASE_NAME:
            return db["id"]

    resp = requests.post(
        f"{METABASE_URL}/api/database",
        headers=headers,
        json={
            "engine": "duckdb",
            "name": DATABASE_NAME,
            "details": {
                "database_file": DUCKDB_PATH_IN_CONTAINER,
                "read_only": True,
                "old_implicit_casting": True,
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    database_id = resp.json()["id"]
    # Cards created immediately after can fail to resolve table names
    # until the initial metadata sync finishes -- found by hitting that
    # race the first time this ran without waiting.
    for _ in range(30):
        status = requests.get(f"{METABASE_URL}/api/database/{database_id}", headers=headers, timeout=10).json()
        if status["initial_sync_status"] == "complete":
            break
        time.sleep(2)
    return database_id


def _get_or_create_card(session: str, database_id: int, name: str, query: str, display: str) -> int:
    headers = {"X-Metabase-Session": session}
    existing = requests.get(f"{METABASE_URL}/api/card", headers=headers, timeout=10).json()
    for card in existing:
        if card["name"] == name:
            return card["id"]

    resp = requests.post(
        f"{METABASE_URL}/api/card",
        headers=headers,
        json={
            "name": name,
            "dataset_query": {
                "type": "native",
                "native": {"query": query},
                "database": database_id,
            },
            "display": display,
            "visualization_settings": {},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _get_or_create_dashboard(session: str, card_ids: list[int]) -> int:
    headers = {"X-Metabase-Session": session}
    existing = requests.get(f"{METABASE_URL}/api/dashboard", headers=headers, timeout=10).json()
    for dashboard in existing:
        if dashboard["name"] == DATABASE_NAME:
            dashboard_id = dashboard["id"]
            break
    else:
        resp = requests.post(f"{METABASE_URL}/api/dashboard", headers=headers, json={"name": DATABASE_NAME}, timeout=30)
        resp.raise_for_status()
        dashboard_id = resp.json()["id"]

    dashcards = [
        {"id": -(i + 1), "card_id": card_id, "row": i * 6, "col": 0, "size_x": 12, "size_y": 6}
        for i, card_id in enumerate(card_ids)
    ]
    resp = requests.put(
        f"{METABASE_URL}/api/dashboard/{dashboard_id}",
        headers=headers,
        json={"dashcards": dashcards},
        timeout=30,
    )
    resp.raise_for_status()
    return dashboard_id


def main():
    _wait_for_metabase()
    session = _get_or_create_session()
    database_id = _get_or_create_database(session)
    card_ids = [
        _get_or_create_card(session, database_id, card["name"], card["query"], card["display"])
        for card in CARDS
    ]
    dashboard_id = _get_or_create_dashboard(session, card_ids)
    print(f"Dashboard ready: {METABASE_URL}/dashboard/{dashboard_id}")


if __name__ == "__main__":
    main()
