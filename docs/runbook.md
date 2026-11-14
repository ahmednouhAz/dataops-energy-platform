# Runbook: what to do when an alert fires

Three alerts exist (ADR 0007), each telling you something different.
Check which one fired before doing anything else -- they point at
different problems.

## 1. Discord: "Flow **daily-energy-platform-run** run `<name>` failed"

**What it means**: a flow *run* raised an exception (Prefect's
`on_failure` hook, `flows/alerts.py`). The scheduler is fine; this
specific run didn't finish.

**Diagnose**:
1. Open the Prefect UI (`http://localhost:4200`) → that flow run → read
   the task logs. The failing task's exception is the actual cause --
   don't guess.
2. Common causes, in likely order: an API returned an error after
   exhausting `pipeline/http_utils.py`'s retries (check the upstream
   API's status directly); a dbt test failed for real (bad data, not a
   transient issue); a genuine code bug introduced by a recent change.

**Fix**:
- Transient (API was down, now isn't): nothing to fix -- the next
  scheduled run (or `docker compose exec worker python -m flows.daily`
  right now) will succeed on its own.
- A dbt test failure: this is `eco2mix_rejected` or a generic test
  catching something real. Read `docs/adr/0004-backfill-approach.md`
  and `models/intermediate/int_eco2mix_checked.sql`'s comments for the
  known categories (DST duplicates, missing-consumption freshest-hours
  gap, etc.) before assuming it's a new problem.
- A code bug: fix it, `pytest` + `dbt build --target ci` locally, PR,
  merge, re-run.

**Verify**: re-run the flow (`docker compose exec worker python -m
flows.daily`), confirm it reaches `Completed` in the Prefect UI.

## 2. Grafana: "Freshness SLO breached (data older than 30h)"

**What it means**: `serving.duckdb`'s newest row is stale. Unlike alert
1, this fires even if the orchestrator never got a chance to run at all
-- it's watching the *data*, not the *runs*.

**Diagnose, in this order** (`docs/slo.md` has the full reasoning):
1. `docker compose ps worker` -- is the container even up? If it
   crashed or was never started, there's no scheduler running at all.
   This is the most common real cause and the easiest to miss if you
   only check "did any run fail" (it didn't fail -- it never ran).
2. If the container is up: Prefect UI → the deployment's flow-run
   history. Any runs in the stale window? If none, the schedule itself
   isn't registered -- check `docker compose logs worker` for "is being
   served and polling for scheduled runs"; if that line is missing, the
   container didn't start `flow.serve()` correctly.
3. If there are runs but they're failing: see alert 1's diagnosis.

**Fix**: `docker compose up -d worker` if the container was down;
otherwise fix whatever alert 1's diagnosis found, then run the flow
manually once to catch up immediately rather than waiting for the next
schedule.

**Verify**: `curl http://localhost:9090/api/v1/query?query=energy_platform_freshness_hours`
(or the Grafana panel) shows a small number again.

## 3. Grafana: "Reject rate SLO breached (over 20%)"

**What it means**: more than 20% of staged eco2mix rows are currently
quarantined in `eco2mix_rejected` -- the same threshold dbt's own
`assert_reject_rate_below_20_percent` test already guards at build
time, now watched continuously.

**Diagnose**:
1. `docker compose exec worker python query.py "select reject_reason, count(*) from eco2mix_rejected group by 1 order by 2 desc"`
   -- which reason dominates tells you what changed.
2. `missing_consumption` spiking: likely the real-time dataset's
   freshest-hours null gap (ADR 0002 addendum) growing because the
   daily flow hasn't re-ingested the trailing window in a while --
   check alert 2 first, this is often a symptom of the same root cause.
3. `unknown_region`/`invalid_timestamp` spiking: the source may have
   changed shape -- check the data contract
   (`datacontract test --server ci contracts/eco2mix_regional.yaml`)
   before assuming it's our bug.
4. `duplicate_region_datetime` spiking well beyond the expected ~24/year
   DST pattern (ADR 0004): something is re-loading overlapping date
   ranges without the expected delete-then-append/merge idempotency --
   check what actually ran recently.

**Fix**: depends entirely on the dominant reason above -- this alert is
a prompt to look, not a single fixed action.

**Verify**: re-run `dbt build`, confirm
`assert_reject_rate_below_20_percent` passes and the Grafana panel
drops back under 20%.
