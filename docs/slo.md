# Freshness SLO

## Objective

**`fct_energy_production`'s newest row must be no more than 30 hours
old**, measured as `now() - max(date_heure)` in the published
`serving.duckdb` (`flows/metrics.py::compute_freshness_hours`, pushed to
Prometheus as `energy_platform_freshness_hours` every run).

## Why 30 hours, not 24

The daily flow (`flows/daily.py`) runs once, at 06:00 UTC
(`flow.serve(cron="0 6 * * *")`). Under normal conditions, freshness
should sit somewhere between a few hours (right after a run) and just
under 24 (right before the next one). 30 hours gives a **6-hour buffer**
past one full day -- enough to not fire on a slightly late run or a
single slow retry cycle (ingest retries up to 3 times at 60s delay, dbt
build up to 2 times at 120s -- a few minutes at most, nowhere near 6
hours), while still catching the case that actually matters: **a run was
silently skipped or has been failing for more than a day.**

## How it's watched

- **Grafana alert rule** `freshness-slo-breach`
  (`monitoring/grafana/provisioning/alerting/rules.yml`): fires when
  `energy_platform_freshness_hours > 30` for 5 minutes straight (the
  `for: 5m` guards against a single flaky scrape), routed to the
  `discord-alerts` contact point.
- This is a **different signal** from Prefect's own `on_failure` hook
  (`flows/alerts.py`, step 12): that one fires the instant a flow *run*
  raises an exception. This one fires on the *data*, and catches cases
  the orchestrator can't see on its own -- e.g. the `worker` container
  itself not running at all, so nothing is even attempting the scheduled
  run, there's simply no flow to fail.

## Reject-rate SLO (bonus, same mechanism)

Mirrors dbt's own `assert_reject_rate_below_20_percent` singular test
(step 6): Grafana alert rule `reject-rate-slo-breach` fires when
`energy_platform_reject_rate > 0.2` for 5 minutes. The dbt test catches
this once, at build time, for the data in that specific build; the
Grafana rule watches it continuously, across every run, after the fact.

## What breaches this SLO in practice (see docs/learning_log.md step 13)

- The `worker` container not running (crashed, Docker Compose not
  started) -- no scheduler, no runs, freshness only grows.
- `ingest_task` or `dbt_build_task` failing repeatedly (API down, a
  genuinely broken rule) -- Prefect's retries are exhausted, the flow
  fails, `publish_task` never runs, `serving.duckdb` keeps yesterday's
  (or older) data.
- A correct run that still can't publish fresher data than it already
  had -- e.g. the upstream API itself hasn't published new data yet. This
  is a real scenario worth distinguishing at the defense: the SLO can
  breach even when every step of *our* pipeline behaved correctly.
