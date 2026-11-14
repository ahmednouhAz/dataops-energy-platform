# Game day postmortem (2026-11-14)

Five scenarios from CLAUDE.md's roadmap: API down, renamed column, bad
data, full disk, wrong rule. Three were rehearsed live today, timed;
one reuses real evidence already produced during step 8 (not re-run,
since nothing would be learned by repeating it identically); one was
deliberately **not** physically performed, for a stated reason.

## 1. API down

**What was done**: pointed `eco2mix.BASE` and `weather.ARCHIVE_URL` at
`http://127.0.0.1:9` (an unused port, instant connection refusal) and
ran `flows.daily.daily_flow()` for real inside the `worker` container.

**Timeline**:
- `12:33:28.367` -- flow run starts.
- `12:33:32` -- first HTTP attempt fails, `http_utils.get_with_retries`
  retries twice more (2s apart), then raises.
- `12:33:32.391` / `12:34:36.402` / `12:35:40.405` -- Prefect's own
  task-level retry (`ingest_task(retries=3, retry_delay_seconds=60)`)
  fires three times, 60 seconds apart.
- `12:36:44.440` -- all retries exhausted, `ingest_task` finally fails.
- `12:36:44.586` -- the Discord `on_failure` hook runs within 150ms and
  logs "DISCORD_WEBHOOK_URL not set; alert not sent" (correct behavior
  with no real webhook configured).

**Total time to alert: ~3 minutes 16 seconds.**

**Finding**: this is dominated by Prefect's own retry delay (3 × 60s =
180s), stacked on top of the lower-level HTTP retries (3 × ~2-5s each).
The two retry layers are each individually reasonable (ADR 0006: one
absorbs a single flaky request, the other absorbs a longer outage), but
their *combination* means a genuine, sustained outage isn't flagged for
over three minutes even though "retries are working exactly as
designed." Not changed today -- flagged as a real tradeoff worth a
deliberate decision (faster detection vs. tolerance for transient
blips), not fixed reflexively mid-game-day.

## 2. Bad data

**What was done**: called `pipeline.ingest._validate_or_refuse` with a
hand-built row containing `eolien: 999999999` (an impossible wind
generation value) against the real `RAW_ECO2MIX` Pandera schema.

**Result**: refused in **1.36 seconds**, `REFUSED: eco2mix batch does
not match the expected schema`, naming the exact column and check that
failed. Nothing loaded (confirmed: the script's own
"LOADED -- THIS SHOULD NOT PRINT" line never printed).

**Finding**: none -- this worked exactly as designed, as fast as a
single Python process can run. Included for a real timing baseline
against the other scenarios, not because anything was wrong.

## 3. Wrong rule

**What was done**: flipped `int_eco2mix_checked.sql`'s
`unknown_region` check from `code_insee_region not in (...)` to
`code_insee_region in (...)` (a realistic typo -- the kind one extra or
missing `not` actually causes) and ran `dbt build` on `dev`.

**Result**: **4.43 seconds** to `Done. PASS=17 WARN=0 ERROR=1 SKIP=25
TOTAL=43`. The unit test `test_duplicate_region_datetime_keeps_latest_load`
failed first (the inverted rule reclassified every known region as
"unknown," pre-empting the duplicate check, since dbt's `case when`
rules apply in order and the first match wins); `int_eco2mix_checked`
itself was then skipped, cascading to 25 total skips including marts,
other tests, and the *other* unit test
(`test_unknown_region_is_rejected`, which never even got the chance to
run and show the real problem directly). Reverted immediately after
confirming the result; `git status` showed a clean tree again.

**Finding**: a single flipped condition broke a unit test that wasn't
the "obvious" one for the change, and masked the unit test that would
have named the actual broken rule directly. This is itself useful
operational knowledge: when a unit test fails, check whether it's
failing *because of* that test's own logic or as a side effect of an
earlier rule in the same `case when` chain producing wrong input to it.
`dbt build`'s skip cascade (not just the first failure) is what makes
this traceable at all.

## 4. Renamed column

**Not re-rehearsed today -- real evidence already exists** from step 8
(`docs/learning_log.md`'s step 8 entry, `CLAUDE.md` section 9): PR #13
(closed, not merged) renamed `consommation` in the fixture to match a
hypothetical supplier change. `datacontract test` caught it immediately
(`contract red`), the PR's `mergeStateStatus` was `BLOCKED`, and
`data-quality` never even reached the Pandera/dbt steps. Re-running an
identical demo today would prove the same mechanism a second time, not
learn anything new -- the real value of a game day is finding *new*
problems, and this one is already load-bearing, real evidence, not a
hypothetical.

## 5. Full disk

**Deliberately not physically rehearsed.** Actually filling the host's
disk is destructive and hard to safely reverse (risk of corrupting
other work on the same machine, including this project's own
multi-hundred-MB `dev.duckdb`), and CLAUDE.md section on destructive
commands is explicit that this class of action needs to be weighed, not
performed reflexively for a rehearsal. Reasoned through instead:

- DuckDB's own behavior on a full disk is to fail the write with an
  I/O error (not silent corruption) -- the failure mode is loud, not
  quiet.
- A failed `dbt build` task (any write failure, disk or otherwise)
  already goes through the exact same alerting path proven in scenario
  1 above (Prefect's `on_failure` hook) once task retries are
  exhausted -- no separate mechanism would be needed.
- The harder problem a full disk actually causes is Docker volumes
  (`minio-data`, `prometheus-data`, `grafana-data`, `metabase-data`,
  `prefect-data`) filling the *host's* disk, not the warehouse file
  specifically -- `docker system df` is the real first diagnostic, not
  anything inside this project's own code.
- Left as a documented gap: this reasoning hasn't been verified against
  a real full-disk condition, unlike every other finding in this
  document. Worth doing in a real staging environment, not this
  desktop, if the opportunity comes up.

## Summary

| Scenario | Rehearsed live? | Time to detection | Mechanism that caught it |
|---|---|---|---|
| API down | Yes | ~3m16s | Prefect task retries exhausted → `on_failure` Discord hook |
| Bad data | Yes | 1.36s | Pandera, `pipeline/schema.py` |
| Wrong rule | Yes | 4.43s | dbt unit test → chain-stop (25 skips) |
| Renamed column | Reused from step 8 (PR #13) | seconds (CI) | ODCS data contract (`datacontract test`) |
| Full disk | No (destructive to rehearse safely) | n/a | Reasoned through, not verified |

**What changed as a result**: nothing in the code -- every mechanism
tested did what it was designed to do. The one open question worth
revisiting is scenario 1's ~3m16s combined retry delay: whether that's
an acceptable detection latency for a project whose daily flow runs
once a day anyway, or whether `ingest_task`'s `retry_delay_seconds=60`
should be shortened for faster failure signaling. Not changed today,
deliberately -- a game day finds things to decide about, it doesn't
have to fix everything in the same sitting.
