# Architecture

## Diagram

```mermaid
flowchart TB
    subgraph sources["Sources"]
        eco2mix["eCO2mix regional\n(ODRE/RTE API)"]
        meteo["Open-Meteo\n(archive API)"]
    end

    subgraph ingest["Ingestion (dlt)"]
        pipeline["pipeline/ingest.py\npipeline/backfill.py"]
        pandera["Pandera validation\npipeline/schema.py"]
    end

    subgraph warehouse["Warehouse (DuckDB)"]
        raw["raw schema\n(untouched, all text)"]
        staging["staging\n(typed, view)"]
        intermediate["intermediate\n(reject_reason, view)"]
        marts["marts\n(star schema, table)\nfct_energy_production\nfct_consumption_weather\ndim_region / dim_energy_source / dim_date\neco2mix_rejected"]
    end

    subgraph orchestration["Orchestration (Prefect)"]
        daily["flows/daily.py\n06:00 UTC schedule"]
        backfill["flows/backfill_flow.py\non demand"]
        alerts["flows/alerts.py\nDiscord on_failure"]
    end

    subgraph publish["Publish"]
        prod["prod.duckdb\n(dbt writes here)"]
        serving["serving.duckdb\n(read-only copy)"]
    end

    subgraph observability["Observability"]
        metrics["flows/metrics.py"]
        pushgw["Pushgateway"]
        prometheus["Prometheus"]
        grafana["Grafana\ndashboard + 2 alert rules"]
    end

    subgraph consumption["Consumption"]
        metabase["Metabase\n3 business-question cards"]
    end

    subgraph governance["Governance"]
        contracts["contracts/*.yaml\nowner, retention, PII"]
        dvc["DVC + MinIO\nreference datasets"]
    end

    eco2mix --> pipeline
    meteo --> pipeline
    pipeline --> pandera --> raw
    raw --> staging --> intermediate --> marts

    daily --> pipeline
    daily --> prod
    prod -. dbt build .-> marts
    daily --> serving
    backfill --> raw
    daily -. on failure .-> alerts
    backfill -. on failure .-> alerts

    daily --> metrics --> pushgw --> prometheus --> grafana
    serving --> metrics
    grafana -. alert rule .-> alerts2["Discord\n(freshness / reject-rate SLO)"]

    serving --> metabase

    contracts -.validates shape of.-> pipeline
```

## Why these layers

- **ELT, not ETL**: raw data loads exactly as the source sent it
  (`raw` schema, every column as text); transformation happens in SQL
  inside the warehouse afterward. A wrong transformation rule can be
  fixed and replayed without re-fetching anything.
- **Medallion**: `raw` (bronze) → `staging`+`intermediate` (silver) →
  `marts` (gold). Each layer does one job: staging types columns and
  repairs nothing-is-lost issues; intermediate applies business rules
  and routes bad rows to quarantine; marts are what a dashboard reads.
- **Write-audit-publish**: dbt writes to `prod.duckdb`; dbt's own tests
  are the audit gate (the daily flow's `dbt_build_task` fails the whole
  run if any test fails); only on success does `publish_task` copy the
  result to `serving.duckdb`. Every downstream reader (Metabase, the
  metrics job) reads `serving.duckdb`, never the file dbt is actively
  writing to -- DuckDB only allows one read-write handle on a file at a
  time (CLAUDE.md section 7), so this is what keeps a dashboard query
  from ever blocking tomorrow's build.
- **Two independent alert paths** (ADR 0007): Prefect's own
  `on_failure` hook fires when a flow *run* crashes; Grafana's alert
  rules fire on the *published data's state* (stale, or too many
  rejects) -- a signal the orchestrator can't see on its own, e.g. the
  whole `worker` container not running at all.

## Where to find more detail

Every non-obvious decision behind this diagram has its own ADR in
`docs/adr/` -- what was decided, why, and what was tried and rejected
first. `docs/learning_log.md` has the step-by-step build history,
including every real bug found along the way (most of them found by
actually running something, not by reasoning about it in advance).
