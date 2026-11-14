# Progress — requirements checklist

Copied from `CLAUDE.md` section 5 (which itself summarizes `course/PROJET.md`).
Tick an item only when it is actually done and verified, not when it is started.

## Version control
- [ ] Git, one branch per change, every change through a pull request (solo: self-review comment + green CI)
- [x] DVC for reference datasets and test samples (`data/reference/`, local remote for now -- ADR 0003)

## Transformation (dbt on DuckDB)
- [x] `sources.yml` for each source with a freshness check (`dbt source freshness`)
- [x] one `stg_` model per source table, `int_` models
- [x] star-schema marts: >= 1 `fct_` and >= 2 `dim_`; >= 8 models in total (11 models: 2 stg, 3 int, 2 fct, 3 dim, 1 quarantine)
- [x] `unique` + `not_null` on every key, `relationships` between facts and dimensions, `accepted_values` on closed-list columns
- [x] >= 2 singular tests and >= 2 unit tests (2 singular: unique key + reject rate; 2 unit: unknown region, duplicate dedup)
- [x] >= 1 incremental model for the big fact table (`fct_energy_production`, proved by loading a new day and checking the exact row delta)
- [x] a description for every mart and every mart column; `dbt docs generate`
- [ ] one warehouse file per environment (`dev.duckdb`, `prod.duckdb`) chosen by the dbt target; CI builds on a sample in seconds

## Quality
- [x] a data contract per source (ODCS), with owner and retention period (`contracts/eco2mix_regional.yaml`, `contracts/weather_hourly.yaml`)
- [x] dbt generic + singular tests, >= 2 unit tests
- [x] a quarantine table (`eco2mix_rejected`)
- [x] (bonus) Pandera validation at the ingestion entrance, refuses an unusable batch before loading (`pipeline/schema.py`, step 3)

## Continuous integration
- [x] GitHub Actions on every PR: lint, pytest, contract, `dbt build` on a sample (`.github/workflows/ci.yml`)
- [x] a red PR cannot be merged (branch protection on `main`, required checks: lint, gitleaks, python-tests, data-quality; demoed with two closed-without-merging PRs, #13 and #14 -- see `docs/learning_log.md` step 8)

## Environment
- [x] `docker compose up` starts the whole platform (step 11: minio, minio-setup, prefect-server, worker -- more services join progressively in later steps, e.g. Prometheus/Grafana in step 13)
- [x] MinIO object storage (step 11; the free official image stopped being publishable in Oct 2025, using the free Chainguard build instead -- see ADR 0005)
- [x] `.env.example` committed, `.env` gitignored, no secret in the repo

## Orchestration (Prefect)
- [x] one scheduled run per day: ingestion -> `dbt build` -> publish (step 12, `flows/daily.py`, `flow.serve(cron="0 6 * * *")`; dashboard refresh joins once step 14 picks a tool -- see ADR 0006)
- [x] automatic retries with delay, an alert on failure, readable logs in the UI (step 12: `@task(retries=..., retry_delay_seconds=...)`, a Discord `on_failure` hook proven to fire on a real failed run, Prefect UI/API both show every attempt)
- [x] backfill: replay history day by day with a date parameter, without duplicates (`pipeline/backfill.py`, step 10; year chunks 2013-01-01..2026-08-31, idempotency proved by re-running a chunk and comparing before/after counts; step 12 adds `flows/backfill_flow.py`, the same logic with per-chunk Prefect retries)

## Ingestion (dlt)
- [x] incremental and idempotent (running twice gives the same result) — proved in step 2 for a 2-day window, and again in step 10 for a full year chunk after the historical backfill
- [x] history loaded by backfill (16,560,648 rows in `fct_energy_production`, >= 1,000,000 rows requirement met -- step 10)

## Continuous delivery
- [x] Docker images published to GHCR on each tag (step 15: tagged `v0.1.0` and `v0.1.1` for real, both published and pulled successfully -- `ghcr.io/ahmednouhaz/dataops-energy-platform`)
- [x] dev and prod environments (already satisfied by steps 4/11/12: dbt `dev`/`prod`/`ci` targets, `PROD_DUCKDB_PATH`/`SERVING_DUCKDB_PATH` vs. interactive `DUCKDB_PATH`)
- [x] documented rollback (step 15: `docs/rollback.md`; rolled back a real running container from `0.1.1` to `0.1.0` and verified via the container's own image + OCI revision label, not just the command's exit code)

## Observability
- [x] duration, rows, rejects and freshness in Grafana (via Prometheus) (step 13: `flows/metrics.py` pushes to Pushgateway every run, dashboard `monitoring/grafana/dashboards/energy_platform.json`)
- [x] an alert on Discord or Slack (step 13: Grafana's own Discord contact point + 2 alert rules, separate signal from step 12's Prefect `on_failure` hook -- see ADR 0007)
- [x] a written freshness objective (SLO) (`docs/slo.md`: 30h, with the reasoning)

## Governance & security
- [x] gitleaks in CI (`.github/workflows/ci.yml`, parallel `gitleaks` job)
- [x] personal data masked (step 16: documented no-PII in each contract since step 7; `macros/mask_pii.sql` + `models/governance/demo_pii_masking.sql` + 2 unit tests prove the masking mechanism works even though nothing in this warehouse needs it)
- [x] owner + retention in each contract (since step 7); documented lineage (`dbt docs generate`, including the step-14 exposure)

## Consumption
- [x] a dashboard (Metabase or Evidence) answering the 3 business questions, reading only from the marts (step 14: Metabase + community DuckDB driver -- Evidence's self-host path has no local-DuckDB-file connector, found while trying it; see ADR 0008). Declared as a dbt exposure (`models/exposures.yml`).

## Final deliverables
- [ ] repo with `main` in defense state and a tag `v1.x`
- [ ] README that lets a stranger run everything
- [ ] architecture diagram
- [ ] ADRs: one page per important choice (what, why, rejected alternatives) in `docs/adr/`
- [ ] runbook: what to do when the alert fires (`docs/runbook.md`)
- [ ] postmortem of the game day (`docs/postmortem.md`)

---

## Roadmap step log

| # | Brick | Status | Date |
|---|---|---|---|
| 0 | Local setup on the desktop | done (PR #2) | 2026-11-12 |
| 1 | Explore the sources | done | 2026-11-12 |
| 2 | Ingestion with dlt | done | 2026-11-12 |
| 3 | Pandera at the entrance | done | 2026-11-12 |
| 4 | dbt project + staging | done | 2026-11-12 |
| 5 | Rules, quarantine, marts in star | done | 2026-11-12 |
| 6 | dbt tests + docs | done | 2026-11-12 |
| 7 | Pytest + data contracts | done | 2026-11-12 |
| 8 | CI quality gate | done | 2026-11-12 |
| 9 | DVC | done | 2026-11-12 |
