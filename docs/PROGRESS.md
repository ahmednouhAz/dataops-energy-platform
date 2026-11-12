# Progress — requirements checklist

Copied from `CLAUDE.md` section 5 (which itself summarizes `course/PROJET.md`).
Tick an item only when it is actually done and verified, not when it is started.

## Version control
- [ ] Git, one branch per change, every change through a pull request (solo: self-review comment + green CI)
- [ ] DVC for reference datasets and test samples

## Transformation (dbt on DuckDB)
- [ ] `sources.yml` for each source with a freshness check (`dbt source freshness`)
- [ ] one `stg_` model per source table, `int_` models
- [ ] star-schema marts: >= 1 `fct_` and >= 2 `dim_`; >= 8 models in total
- [ ] `unique` + `not_null` on every key, `relationships` between facts and dimensions, `accepted_values` on closed-list columns
- [ ] >= 2 singular tests and >= 2 unit tests
- [ ] >= 1 incremental model for the big fact table
- [ ] a description for every mart and every mart column; `dbt docs generate`
- [ ] one warehouse file per environment (`dev.duckdb`, `prod.duckdb`) chosen by the dbt target; CI builds on a sample in seconds

## Quality
- [ ] a data contract per source (ODCS), with owner and retention period
- [ ] dbt generic + singular tests, >= 2 unit tests, a quarantine table

## Continuous integration
- [ ] GitHub Actions on every PR: lint, pytest, contract, `dbt build` on a sample
- [ ] a red PR cannot be merged (branch protection on `main` with required status checks)

## Environment
- [ ] `docker compose up` starts the whole platform
- [ ] MinIO object storage
- [ ] `.env.example` committed, `.env` gitignored, no secret in the repo

## Orchestration (Prefect)
- [ ] one scheduled run per day: ingestion -> `dbt build` -> dashboard refresh
- [ ] automatic retries with delay, an alert on failure, readable logs in the UI
- [ ] backfill: replay history day by day with a date parameter, without duplicates

## Ingestion (dlt)
- [x] incremental and idempotent (running twice gives the same result) — proved in step 2 for a 2-day window; full backfill is step 10
- [ ] history loaded by backfill

## Continuous delivery
- [ ] Docker images published to GHCR on each tag
- [ ] dev and prod environments
- [ ] documented rollback

## Observability
- [ ] duration, rows, rejects and freshness in Grafana (via Prometheus)
- [ ] an alert on Discord or Slack
- [ ] a written freshness objective (SLO)

## Governance & security
- [ ] gitleaks in CI
- [ ] personal data masked (document explicitly: our data has no personal data; show the masking mechanism anyway)
- [ ] owner + retention in each contract; documented lineage

## Consumption
- [ ] a dashboard (Metabase or Evidence) answering the 3 business questions, reading only from the marts

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
