# DataOps Energy Platform

A complete data platform for French regional electricity data: automatic
daily ingestion, a tested warehouse, CI/CD, orchestration, monitoring,
and governance. Built solo, step by step -- see `CLAUDE.md` for the full
roadmap and `docs/learning_log.md` for what was learned (and what broke)
at each step.

**Four promises:** **Automatic** (data arrives every day without a
human) · **Reliable** (wrong data is blocked before reaching a
dashboard) · **Reproducible** (clone the repo, run one command) ·
**Observable** (we always know whether data is fresh, complete and
correct).

## Architecture

See `docs/architecture.md` for the full diagram and explanation. In
short: [dlt](https://dlthub.com) ingests two sources (eCO2mix regional
electricity data, Open-Meteo weather) into raw tables in
[DuckDB](https://duckdb.org); [dbt](https://www.getdbt.com) transforms
them through staging → intermediate → marts (a star schema); a
[Prefect](https://www.prefect.io) flow runs the whole thing once a day
and publishes a read-only copy for the dashboard; Prometheus/Grafana
watch freshness and data quality; a self-hosted
[Metabase](https://www.metabase.com) dashboard answers the project's 3
business questions (`docs/business_questions.md`).

## Run it

Requires Docker Desktop. Nothing else needs to be installed on the host
to run the full platform.

```
git clone https://github.com/ahmednouhAz/dataops-energy-platform.git
cd dataops-energy-platform
cp .env.example .env   # fill in real admin passwords before exposing this beyond localhost
docker compose up -d
```

This starts everything: object storage (MinIO), the orchestrator
(Prefect server + a worker running the daily flow on its own 06:00 UTC
schedule), metrics (Prometheus + Pushgateway + Grafana), and the
dashboard (Metabase, with its database connection and the 3
business-question cards built automatically on first run -- no manual
click-through).

| Service | URL | Notes |
|---|---|---|
| Metabase (dashboard) | http://localhost:3001 | admin login from `.env`'s `METABASE_ADMIN_EMAIL`/`PASSWORD` |
| Grafana (metrics/alerts) | http://localhost:3000 | admin / `GRAFANA_ADMIN_PASSWORD` |
| Prefect (orchestration) | http://localhost:4200 | flow runs, logs, the daily schedule |
| Prometheus | http://localhost:9090 | raw metrics, if you want to query them directly |
| MinIO console | http://localhost:9001 | object storage, backs the DVC remote |

To run something ad hoc inside the same environment the orchestrator
uses (no local Python/dbt install needed):

```
docker compose exec worker pytest
docker compose exec worker dbt build --target prod
docker compose exec worker python -m flows.backfill_flow --start-date 2013-01-01 --end-date 2026-08-31
```

### Local interactive development

For day-to-day work without Docker (faster iteration while editing
models), use the `.venv` + `dev` dbt target instead -- see `CLAUDE.md`
section 2 for setup, and `CLAUDE.md` section 7 for why `dev.duckdb` and
the orchestrated `prod.duckdb`/`serving.duckdb` are kept deliberately
separate (DuckDB only allows one read-write handle on a file at a time).

## Key docs

- `docs/business_questions.md` -- the 3 questions the dashboard answers.
- `docs/architecture.md` -- the full architecture diagram and the design
  decisions behind it.
- `docs/PROGRESS.md` -- the project brief's requirements checklist,
  ticked as each was actually verified.
- `docs/learning_log.md` -- what was built, what broke, and what was
  learned at every step of the roadmap -- the most detailed record of
  *why* things are the way they are.
- `docs/adr/` -- one page per significant decision (what, why, what was
  rejected and why).
- `docs/slo.md` -- the written freshness SLO and how it's watched.
- `docs/runbook.md` -- what to do when an alert fires.
- `docs/rollback.md` -- the tested procedure for rolling back a bad
  release.
- `docs/postmortem.md` -- the rehearsed game day: what was broken on
  purpose, how long it took to notice and fix, and what changed as a
  result.

## Status

Steps 0-16 of the roadmap are done (see `CLAUDE.md` section 9 for the
exact current state). `docs/PROGRESS.md` tracks the project brief's full
requirements checklist.
