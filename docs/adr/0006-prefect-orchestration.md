# ADR 0006 — Prefect orchestration: daily flow, backfill flow, alerts

## Decision
- `flows/daily.py`: `ingest -> dbt build --target prod -> publish`, as
  Prefect tasks (`@task`) inside one `@flow`. `python -m flows.daily
  --serve` registers a daily 06:00 UTC schedule and keeps running to
  execute it (`flow.serve(cron="0 6 * * *")`) -- this is what
  `docker-compose.yml`'s `worker` service now runs by default, so "one
  scheduled run per day" is live as soon as `docker compose up` is.
- `flows/backfill_flow.py`: the exact chunk logic `pipeline/backfill.py`
  already proved correct in step 10, with each year chunk as a retried
  Prefect task instead of a plain loop iteration. Invoked on demand
  (`python -m flows.backfill_flow --start-date ... --end-date ...`), not
  scheduled -- a backfill is something you run once with a specific range,
  not a recurring job.
- `flows/alerts.py`: a Discord webhook POST, wired as both flows'
  `on_failure` hook. Logs instead of sending if `DISCORD_WEBHOOK_URL`
  isn't set (`.env.example`), so the flows run the same with or without a
  real Discord server configured.
- Retries at two layers, each catching a different kind of failure:
  `pipeline/http_utils.py::get_with_retries` (step 10) retries one flaky
  HTTP request a few seconds apart; Prefect's own `@task(retries=...,
  retry_delay_seconds=...)` retries a whole task minutes later if that
  still wasn't enough (a longer outage, a transient dbt failure). Both are
  visible: the HTTP layer prints to the task's own log, Prefect's own
  retries show up as separate, numbered attempts in the UI.
- Prefect server image pinned to `prefecthq/prefect:3.9.2-python3.12`,
  matching the `prefect==3.9.2` client pinned in `requirements.txt`
  exactly (not a range, unlike the rest of the file) -- found a client/
  server version-mismatch warning the first time they didn't match (see
  below), and a client talking to a much older or newer server is exactly
  the kind of thing worth pinning tightly rather than letting drift.

## "Refresh" is deliberately not in the flow yet
The roadmap's step 12 deliverable says "ingest -> dbt build -> publish ->
refresh". There's no dashboard yet (step 14 picks the tool -- Metabase or
Evidence), and "refresh" means something completely different depending
on which one it ends up being (a cache-invalidation API call for Metabase,
a rebuild command for Evidence). Stubbing out a `refresh_task()` today
that does nothing, or guesses at an API that might not match the eventual
tool, would be the exact kind of "hide magic" / fake verification
CLAUDE.md warns against. The comment in `daily_flow` marks exactly where
it joins once step 14 picks a tool -- same call already made for
`prefect-server` running with no flows yet in step 11, before step 12
existed.

## A real bug, found only by actually running the flow once
The daily flow's first real run (inside the worker container, live APIs,
not a fixture) failed: `weather.fetch_weather_rows` got a `400 Bad
Request` from Open-Meteo for a date one day in the future. Root cause: the
two sources use different end-date conventions, documented back in step
2's CLI -- eco2mix's own `/records`/`/exports` endpoints treat `end_date`
as **exclusive**, Open-Meteo's archive API treats it as **inclusive**, and
`pipeline/ingest.py::run_ingest` was passing one shared `end_date` value
straight to both. This had been a latent inconsistency since step 2: every
existing caller (the CLI, used by hand) happened to pick values that never
exercised "ask for data through today" for both sources in the same call,
so it never surfaced. `flows/daily.py`'s automatic default (a trailing
window ending "tomorrow", to catch today) was the first caller to actually
hit it.

`pipeline/backfill.py::_load_weather_chunk` had already solved this exact
problem in step 10 by subtracting one day from `chunk_end` before calling
weather's fetch. Applied the same fix inside `run_ingest` itself (not just
in `flows/daily.py`), so every caller -- the CLI included -- now gets a
single, consistent "exclusive for both sources" contract instead of the
old asymmetric one. `pipeline/ingest.py`'s CLI help text updated to match.
Confirmed fixed: re-ran the daily flow, both sources fetched successfully,
`dbt build --target prod` reached `PASS=39`.

## A false alarm, not a pipeline bug
The very first attempt at the backfill-flow smoke test also failed, with
`dlt.common.configuration.exceptions.InvalidNativeValue` on a path that
looked fine. Traced to Git Bash's own path-mangling of an absolute POSIX
path (`/tmp/...`) passed through `docker compose exec -e VAR=...` on
Windows -- the same class of problem ADR 0005 already hit with
`--entrypoint /bin/sh`, just in a different command. Re-ran with a
relative path instead and it worked immediately. Documented here only so
the exam/defense doesn't mistake "a Windows terminal quirk while testing"
for "a bug in the flow code" -- it wasn't, and the fix was in the test
command, not in any committed file.

## Alternatives rejected
- A full Prefect work pool + deployed worker (the "production" Prefect
  pattern): real overkill for one scheduled flow on one machine.
  `flow.serve()` is Prefect's own documented lightweight alternative for
  exactly this case, and is what ADR 0001 already meant by "Prefect is
  lighter than Airflow for a solo project" -- this is where that choice
  actually pays off.
- Stubbing a fake `refresh_task()` now: rejected above, under "Refresh".
- Using `apprise` (pulled in as a transitive Prefect dependency, supports
  a `discord://` URL scheme) instead of a plain `requests.post`: Discord's
  webhook API is one documented HTTP POST with a JSON body; adding a
  library to wrap one POST call would hide, not simplify, what's
  happening.

## Verification
- `docker compose exec worker python -m flows.daily` (one-shot run):
  `ingest_task` fetched 3408 eco2mix + 864 weather rows, `dbt_build_task`
  reached `PASS=39`, `publish_task` copied `prod.duckdb` -> `serving.duckdb`
  (confirmed both files exist, same byte size).
- The flow's first run (before the end-date fix) is recorded as `FAILED`
  in Prefect's own history (queried via `/api/flow_runs/filter`), and the
  Discord hook fired and logged correctly with no webhook configured --
  proving the alert path runs on a real failure, not just in a unit test.
- `flows/backfill_flow.py` smoke-tested on a throwaway one-day range
  (`DUCKDB_PATH` pointed at a scratch file, never touching the real
  `dev.duckdb`): task completed, chunk loaded (576 eco2mix + 288 weather
  rows), visible as `Completed` in Prefect's history.
- `docker compose up -d worker` (serve mode, the actual default now):
  logs confirm `Your flow 'daily-energy-platform-run' is being served and
  polling for scheduled runs!`; queried the deployment via
  `/api/deployments/<id>` and confirmed `schedule.cron == "0 6 * * *"`,
  `active: true`.
- `tests/test_alerts.py` (2 new unit tests): no webhook configured ->
  `requests.post` never called; webhook configured -> called once with
  the exact expected URL/payload. `ruff check .` clean, 17/17 pytest
  passing (15 previous + 2 new).
