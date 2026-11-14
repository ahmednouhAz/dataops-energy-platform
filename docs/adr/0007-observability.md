# ADR 0007 — Observability: Prometheus, Grafana, and two separate alert paths

## Decision
- `flows/metrics.py::push_run_metrics` pushes six gauges (duration, rows
  loaded per source, rows rejected, reject rate, freshness hours, run
  success) to a Prometheus **Pushgateway** at the end of every
  `flows/daily.py` run, success or failure (`try/finally` in
  `daily_flow`). A batch job can't be scraped the normal way -- it isn't
  a server with a `/metrics` endpoint running all day -- Pushgateway is
  exactly the pattern for this.
- `docker-compose.yml` adds `pushgateway`, `prometheus` (scrapes the
  gateway, `monitoring/prometheus.yml`), and `grafana` (provisioned on
  startup: one Prometheus datasource, one dashboard, one Discord contact
  point, two alert rules -- `monitoring/grafana/provisioning/`).
- **Two independent alert paths**, deliberately not merged into one:
  - `flows/alerts.py`'s `on_failure` hook (step 12) fires when a flow
    *run* raises -- an orchestration-level signal.
  - Grafana's alert rules (this step) fire on the *published data's*
    state -- `energy_platform_freshness_hours > 30` for 5m,
    `energy_platform_reject_rate > 0.2` for 5m. These catch cases the
    orchestrator literally cannot see, like the whole `worker` container
    not running at all (no flow, so nothing to "fail").
- Written freshness SLO in `docs/slo.md`: 30 hours, derived from the
  06:00 UTC daily schedule plus a 6-hour buffer (see that doc for the
  reasoning).

## Three real bugs, found only by actually pushing a real run's metrics

1. **Grafana crash-looped on an empty `DISCORD_WEBHOOK_URL`.** The
   Discord contact point's provisioning validation refuses to start at
   all if the URL setting is empty (`could not find webhook url property
   in settings`) -- unlike `flows/alerts.py`'s own graceful
   log-instead-of-send. `.env.example` leaves `DISCORD_WEBHOOK_URL` empty
   on purpose (step 12, still correct for the worker service), so Grafana
   needed its own fallback: `docker-compose.yml`'s `grafana` service uses
   `${DISCORD_WEBHOOK_URL:-https://discord.com/api/webhooks/000000000000000000/placeholder}`
   -- Compose's own default-value syntax, not a second env var to
   configure. The rule still provisions and shows up in the UI either
   way; it just has nowhere real to deliver until a real webhook is set.
2. **`Duplicated timeseries in CollectorRegistry` on the very first real
   push.** Created two separate `Gauge("energy_platform_rows_loaded",
   ...)` objects (one per source) instead of one `Gauge` with two
   `.labels()` calls -- `prometheus_client` registers a metric's name at
   `Gauge()` construction time, so the second object with the same name
   collided. Fixed by constructing the gauge once and calling
   `.labels(source=...).set(...)` twice on the same object.
3. **`Binder Error: Catalog "prod" does not exist!`, only on views, never
   on tables.** `dbt build --target prod` compiles every cross-schema
   reference inside a *view* (`stg_eco2mix_regional`, which does
   `{{ source(...) }}`) as `prod.raw....` -- `prod` is the **target
   name** dbt-duckdb uses as the database/catalog alias, not derived from
   the file path. `publish_task` copies the raw bytes of `prod.duckdb` to
   `serving.duckdb`, which carries that compiled `prod.`-qualified SQL
   along with it. Opening `serving.duckdb` with a plain
   `duckdb.connect(path, read_only=True)` has no catalog literally named
   `prod` in that connection, so any view crossing catalogs internally
   fails to resolve -- while *tables* (materialized, no stored
   cross-catalog reference) read back just fine, which is what made this
   confusing at first: `fct_energy_production` (table) worked,
   `stg_eco2mix_regional` (view) didn't, same file, same connection
   style. Fixed by attaching the file under the matching alias instead of
   connecting to it directly: `duckdb.connect(":memory:")` then
   `attach '<path>' as prod (read_only)` then `use prod` -- exactly what
   dbt-duckdb itself does internally.

## Why query `serving.duckdb`, not `prod.duckdb`
Same write-audit-publish split step 11/12 already built: observability
reads the *published* copy, never the file dbt is actively writing to.
Querying `prod.duckdb` directly from a second process while `dbt build`
might be running would hit DuckDB's single-writer constraint
(CLAUDE.md section 7) for no benefit -- `serving.duckdb` is already a
complete, consistent snapshot by the time `publish_task` finishes.

## Why reject rate is a whole-dataset snapshot, not "this run's rejects"
There's no cheap way to isolate "rows rejected by today's batch
specifically" without a run marker nothing currently writes -- and the
dbt-level guard this already has (`assert_reject_rate_below_20_percent`,
step 6) is itself a whole-dataset check, not a per-run one. Watching the
exact same number continuously in Grafana is more useful than inventing
a differently-scoped number that wouldn't match what the build already
alerted on.

## Alternatives rejected
- A Grafana "webhook" contact point posting to a custom endpoint instead
  of its native "discord" integration: Grafana's Discord type already
  posts in the exact format Discord expects, with zero code -- the
  problem (`flows/alerts.py` needed a hand-written POST because *no*
  built-in Prefect integration does this) doesn't apply here.
- Merging the two alert paths into one (e.g. having Grafana also watch
  `energy_platform_run_success`): rejected under "Decision" above --
  Prefect already owns "did the run crash" better than a polled metric
  ever could (it has the actual exception, not just a 0/1 gauge), and
  Grafana owns "does the published data look wrong" better than Prefect
  ever could (Prefect has no idea what a dbt test result means).
- Computing freshness/reject-rate inside the dbt run itself (a dbt
  macro or test) instead of a separate Python read: rejected because
  Prometheus needs a *value over time*, not a pass/fail at build time --
  this is explicitly what Grafana adds on top of the dbt tests that
  already exist (step 6), not a replacement for them.

## Verification
- `docker compose up -d grafana`: starts and stays up with the
  Compose-level Discord URL fallback (previously crash-looped,
  `Exited (1)`, without it).
- Dashboard loaded: `GET /api/search?type=dash-db` returns "Energy
  Platform - Daily Run".
- Alert rules loaded: `GET /api/v1/provisioning/alert-rules` returns both
  `freshness-slo-breach` and `reject-rate-slo-breach`.
- Contact point loaded: `GET /api/v1/provisioning/contact-points` returns
  `discord-alerts` (type `discord`, URL redacted as a secure setting).
- Ran `flows.daily` for real inside the worker container: metrics pushed
  without error, then confirmed via Prometheus's own query API --
  `energy_platform_freshness_hours` ≈ 0.36h, `energy_platform_rows_loaded`
  with `source="eco2mix"`/`"weather"` labels (3124/864), `reject_rate`
  ≈ 0.127 -- all real numbers from the actual warehouse, not placeholders.
- `tests/test_metrics.py` (5 new unit tests, tiny hand-built DuckDB
  fixtures): missing file -> `inf`/`(0, 0, 0.0)`; empty table -> `inf`;
  a known 2-rejected/10-total fixture -> exactly `0.2`. `ruff check .`
  clean, pytest passing (22 total before this step's own tests are
  counted again at merge time).
