# Learning log

One entry per roadmap step. Each entry: what was done, what I learned, my answers to
the step's questions. Written as I go, in "just do it, explain after" mode when I ask
Claude to move fast (see CLAUDE.md rule 8).

---

## Step 0 — Local setup on the desktop PC (2026-11-12)

### What was done
- Checked the machine: Python (only 3.14 was installed), Git, Docker CLI/daemon,
  GitHub CLI (`gh`, already logged in as `ahmednouhAz`), git identity.
- Installed **Python 3.12** with `winget install Python.Python.3.12`, alongside the
  existing 3.14 (not replacing it), because `dbt-duckdb` does not support 3.14 yet.
  Windows's `py` launcher (`py -0p`) can now list and pick between both.
- Started the Docker Desktop application so the daemon is running (the CLI
  `docker --version` answers even when the daemon isn't started — that only proves the
  client is installed, not that containers can run; `docker ps` is the real test).
- Turned this folder into the real clone of the GitHub repo
  (`ahmednouhAz/dataops-energy-platform`): `git init`, added `origin`, fetched, and
  reset `main` to `origin/main`. Safe because there were zero local commits yet, and
  none of the files already on this machine (`CLAUDE.md`, `course/`) exist on the
  remote, so nothing was overwritten.
- Found that `.gitignore` did **not** actually exclude `course/` or the local
  `.claude/` settings folder, even though `CLAUDE.md` assumed `course/` was already
  ignored. Fixed `.gitignore` to add both.
- Added `CLAUDE.md` to the repo (it is meant to be committed — it's the project's
  instructions file, not a secret or generated file).
- Created this file and `docs/PROGRESS.md` (the requirements checklist copied from
  `CLAUDE.md` section 5, to tick off as the project advances).
- Created a Python 3.12 virtual environment (`.venv`) at the repo root with
  `py -3.12 -m venv .venv`, activated it, and installed `requirements.txt`.

### Why this matters for the four promises
- **Reproductible**: if the Python version, the git remote, or the ignored files are
  wrong from day one, nobody (including future me) can redo this setup the same way.
  Fixing `.gitignore` now avoids accidentally publishing the teacher's `course/`
  material later.

### Answers to the Step 0 questions
- **Q1 (why install Python 3.12 alongside 3.14 instead of replacing it?):**
  `dbt-duckdb` doesn't support Python 3.14 yet (it's brand new). Replacing 3.14
  would break anything else on the machine that depends on 3.14, and would mean
  redoing the switch later if another tool needs 3.14 again. The `py` launcher lets
  every project pick its own version (`py -3.12 ...`), so there's no reason to
  remove either.
- **Q2 (why didn't `docker --version` prove Docker was ready?):**
  `docker --version` only asks the **client** binary to print its own version — it
  doesn't talk to the daemon at all. The daemon (`dockerDesktopLinuxEngine`) is a
  separate background process that has to be started (opening the Docker Desktop
  app) before any container can actually run. `docker ps` is the real test because
  it has to successfully reach the daemon to list containers; it's exactly what
  failed with `failed to connect to the docker API` before Docker Desktop was
  opened.

---

## Step 1 — Explore the sources (2026-11-12)

### What was done
- Wrote `scripts/explore_eco2mix.py`: searches the ODRÉ catalog for `eco2mix`
  datasets (ODSQL `search(field, "text")`, not `like` — `like` silently returned 0
  matches with no error, `search()` is the right function for substring matching),
  then inspects a 5-record sample and the oldest/newest `date_heure` of both the
  definitive (`eco2mix-regional-cons-def`) and real-time (`eco2mix-regional-tr`)
  datasets.
- Wrote `scripts/explore_weather.py`: requests the last 10 days of hourly weather
  for Paris from the Open-Meteo archive API and counts nulls; also tested
  requesting tomorrow's date directly from the shell to find the API's actual
  allowed range.
- Found that `eco2mix-regional-cons-def` and `eco2mix-regional-tr` do **not** share
  one schema (`eolien` is a string in one and an int in the other; three other
  fields flip the other way; one has 2 extra columns; the junk trailing column has
  a different name in each). Documented in `docs/adr/0002-source-exploration.md`.
- Found that `CLAUDE.md`'s claim "the archive lags a few days" was **wrong**: as of
  2026-11-12 the Open-Meteo archive API answers up to and including today with zero
  nulls; requesting tomorrow gives an explicit 400 error naming today as the upper
  bound of the allowed range. Corrected `CLAUDE.md` §7 and recorded the real risk
  (recent days use a forecast-model blend that can later be revised — an accuracy
  risk, not a completeness one) in ADR 0002.
- Queried the eco2mix dataset with `group_by=code_insee_region,libelle_region` to
  get the authoritative list of the 12 mainland France regions (Corsica is not in
  the dataset — it's on a separate grid), then built `seeds/regions.csv` by picking
  one representative city (the regional capital) per region with its lat/lon for
  the Open-Meteo calls. Region names in the CSV are written without accents
  (`Ile-de-France`, not `Île-de-France`) to avoid encoding issues later in dbt
  seeds and CSV tooling.

### Why this matters for the four promises
- **Fiable**: finding the definitive/real-time schema mismatch *now*, before
  staging exists, means the `try_cast`-everything rule in step 4 is designed from
  real evidence, not an assumption — and the Open-Meteo correction prevents writing
  a freshness SLO around a lag that doesn't actually exist.

### Answers to the Step 1 questions (originally posed to me, answered here per
the "just do it" rule)
- **Q1 (which field has a surprising type, and which quality dimension does it
  concern?):** `eolien` arrives as the string `'193'` in the definitive dataset,
  while every other MW measurement in the same record (`consommation`, `thermique`,
  `nucleaire`, `solaire`, `hydraulique`, `bioenergies`, `ech_physiques`) arrives as
  an `int`. This is a **Cohérence** problem: the same kind of quantity (a power
  measurement in MW) is encoded two different ways depending on the column — and,
  as the real-time dataset showed, even depending on which of the two sources
  produced the row (`eolien` is an int there, while `pompage` and the battery
  columns become strings instead). It isn't really a **Validité** problem yet,
  because the string value is a perfectly valid number — it just hasn't been cast.
- **Q2 (does `total_count` alone prove we'll reach 1M warehouse rows?):** No.
  `total_count` counts rows in the **source**, not rows that will end up in the
  warehouse's fact table. Three things can make the final number different: (1) we
  might not backfill 100% of the 2.87M history, (2) quarantine in
  `int_eco2mix_checked` removes some rows from the clean path, and (3) how the fact
  table is modeled changes the row count a lot — one row per region×timestamp stays
  close to 2.87M, but unpivoting into one row per region×timestamp×energy-source
  (as sketched in `CLAUDE.md` §7, ~8 sources) multiplies it to roughly 20M. So
  2.87M is a strong signal we're far above the 1M threshold, but the number that
  actually counts is whatever remains in `fct_energy_production` after modeling and
  quarantine, not the API's raw `total_count`.

### Not yet done (flagged for step 2)
- The bulk `/exports/{format}` endpoint (needed for an efficient backfill instead
  of paginating `/records`) has not been tested yet.

---

## Step 2 — Ingestion with dlt (2026-11-12)

### What was done
- `pipeline/sources/eco2mix.py`: a dlt resource that pages through the
  Opendatasoft `/records` endpoint (100 rows/page) and picks the definitive or
  real-time dataset per date using the 2026-08-31 cutover found in ADR 0002. All
  the measurement columns that flip type between the two datasets (`eolien`,
  `pompage`, the battery columns, etc.) are forced to `text` via the resource's
  `columns=` hint, so `raw.eco2mix_regional` stays consistent no matter which
  dataset a row came from — same philosophy as TP3's `all_varchar = true`:
  raw keeps the exact value the API sent, typing happens in staging (step 4).
- `pipeline/sources/weather.py`: a dlt resource that reads `seeds/regions.csv`
  and calls the Open-Meteo archive API once per region.
- `pipeline/ingest.py`: CLI entrypoint, `python -m pipeline.ingest --start-date
  ... --end-date ...`, loading both sources with `write_disposition="merge"`
  into `raw` in `dev.duckdb` (path overridable via `DUCKDB_PATH`).
- `query.py` at the repo root (TP3 pattern): a 10-line read-only query tool.
  Had to add `sys.stdout.reconfigure(encoding="utf-8")` — Windows' default
  console encoding (cp1252) can't print DuckDB's box-drawing table characters,
  so `query.py "show tables"` crashed with `UnicodeEncodeError` until fixed.
- **Proved idempotency**: loaded 2026-11-10 to 2026-11-12, got 2304 eco2mix rows
  and 864 weather rows; ran the exact same command again; counts unchanged.
  Also checked directly for duplicate `(code_insee_region, date_heure)` pairs —
  zero. This works because of two things together, not one: `primary_key=`
  tells dlt which columns identify "the same row", and
  `write_disposition="merge"` tells it to upsert on that key instead of
  appending. Either one alone wouldn't be enough — a primary key with
  `write_disposition="append"` would still duplicate rows.
- Row counts matched hand-calculated expectations: 2 days of real-time data
  (15-min granularity, confirmed in ADR 0002) × 12 regions = 2304; 3 inclusive
  days of weather × 24h × 12 regions = 864. Checking this arithmetic by hand
  is what actually proves the pipeline isn't silently dropping or duplicating
  rows — a passing run with the wrong count would still print "LOADED" with
  no error, same lesson as TP1's "a script can run without error and still be
  wrong".
- `dev.duckdb` does not show up in `git status` — the existing `*.duckdb` rule
  in `.gitignore` (from the original project skeleton) already covered it.

### Why this matters for the four promises
- **Reproductible**: idempotency is what makes "run it again" a safe operation
  instead of a risk — a flow (step 12) or a human re-running a failed day never
  creates duplicates.
- **Fiable**: the type conflict found in step 1 is now actually neutralized at
  load time, not just written down.

### A question the individual exam could ask, answered here
**"The eCO2mix API renames `eolien` to `wind_mw` tomorrow. What breaks, and
where do you fix it?"** Nothing breaks immediately in `raw` — dlt would just
start loading a new column `wind_mw` (text, by schema evolution) alongside the
old `eolien`, which would now be `null` for every new row (not an error, a
silent gap). The real break happens downstream, in staging (step 4), the first
place that reads `eolien` by name — that model would need its `eolien` column
cast replaced by `coalesce(wind_mw, eolien)` or renamed outright, and a
`dbt source freshness`/schema test would be the thing that actually surfaces
the problem instead of a human noticing a blank chart weeks later.

### Not yet done (flagged for later steps)
- The bulk `/exports/{format}` endpoint, for an efficient full-history backfill
  (step 10) — still only tested with `/records` pagination so far.

---

## Step 3 — Pandera at the entrance (2026-11-12)

### What was done
- `pipeline/schema.py`: two Pandera `DataFrameSchema`s, one per source.
  - `RAW_ECO2MIX` uses **`strict=False`**: the definitive and real-time datasets
    genuinely have different optional columns (ADR 0002 again -- `eolien_terrestre`/
    `eolien_offshore` only in one, `column_30` vs `column_68`), so treating "an
    extra column" as an error would make the schema permanently wrong for one of
    the two sources. `strict=False` still requires every *listed* column to be
    present -- it only stops flagging the columns we didn't list.
  - `RAW_WEATHER` uses **`strict=True`**: one source, one stable set of fields, so
    an unexpected extra/missing column really is worth refusing immediately. This
    is the direct TP4 case.
  - `code_insee_region` is checked against `pa.Check.isin(...)`, built from
    `seeds/regions.csv` at import time rather than a hard-coded list, so there is
    one single source of truth for "the 12 known regions".
  - Numeric columns use a reusable `_mostly_between(low, high)` check factory
    (same idea as TP4's `_mostly_plausible`, generalized since we need it on
    several columns instead of one).
- Restructured `pipeline/sources/eco2mix.py` and `weather.py`: the fetch logic
  is now a plain function (`fetch_eco2mix_rows`, `fetch_weather_rows`) that
  returns a list instead of a `@dlt.resource` generator. This is what makes
  Pandera validation possible *before* loading: `pipeline/ingest.py` fetches
  the whole batch into memory, validates it, and only on success wraps it as
  a `dlt.resource(...)` and calls `pipeline.run(...)`. On failure it prints
  `REFUSED: ...` with the failing checks and `sys.exit(1)` -- nothing is
  loaded, exactly like TP4's `load_raw.py`.
- Verified with real data:
  - `.venv\Scripts\python.exe -m pipeline.ingest --start-date 2026-11-11 --end-date 2026-11-12` loads cleanly (1152 eco2mix rows, 576 weather rows), no `REFUSED` message.
  - A synthetic batch with `code_insee_region: '99'` (a region that doesn't
    exist) is `REFUSED`, exits 1, and the real call never reaches the dlt load
    step for either source.
  - A synthetic weather batch with one extra undeclared column is refused by
    `strict=True` with `column_in_schema` as the failure.
  - Re-checked idempotency after the refactor: re-running an overlapping date
    range still gives `count(*) == count(distinct key)` -- the restructuring
    didn't change the merge behavior from step 2.
  - Confirmed mixed-type coercion works: a batch with `eolien` as `'193'`
    (string, from the definitive dataset) mixed with `eolien` as `207` (int,
    from real-time) coerces cleanly to `float64` under `coerce=True`, which is
    exactly the step-1 finding this schema exists to guard against.

### A design choice worth noting
`pipeline/ingest.py` validates **both** sources before loading **either** one.
If eco2mix is refused, the script exits before even fetching weather. This
means one CLI call represents one atomic "day's ingestion" -- a half-loaded
day (eco2mix in, weather refused) was judged worse than an all-or-nothing
failure, for a single script invocation. This isn't free: a transient failure
in one source currently blocks a perfectly good load of the other. Worth
revisiting once Prefect (step 12) orchestrates each source as its own retryable
task instead of one combined script run.

### A question the individual exam could ask, answered here
**"Pandera already validates the data -- why do we still need dbt tests in
step 5?"** They check different things, not the same thing twice. Pandera
judges a *whole batch* at the moment of loading: is this file/response shaped
right, and are most of its values plausible? It can't look at one row in
isolation against the dataset's history, and it runs once, outside the
warehouse. dbt's tests run *inside* the warehouse, row by row, every time
`dbt build` runs, and they can reference other models (`relationships`,
`unique` across the full history, not just this batch). A single bad
consumption value in an otherwise fine batch sails through Pandera's
"95% plausible" check -- it is exactly the kind of thing the row-level
`int_eco2mix_checked` quarantine rule (step 5) exists to catch.

---

## Step 4 — dbt project + staging (2026-11-12)

### What was done
- `dbt_project.yml` and `profiles.yml` at the repo root (TP3 convention, not
  under a `dbt/` subfolder). Profile `energy_platform` has three targets --
  `dev` (`dev.duckdb`), `prod` (`prod.duckdb`), `ci` (`ci.duckdb`) -- so the
  warehouse file is chosen by `--target`, never hard-coded in a model.
- **Found and fixed a second gitignore bug** (after the `course/`/`.claude/`
  one in step 0): the existing rules ignored `dbt/target/`, `dbt/logs/`,
  `dbt/dbt_packages/`, assuming a `dbt/` subfolder that doesn't exist in our
  layout. Fixed to the root-level `target/`, `logs/`, `dbt_packages/` that
  dbt actually creates here.
- `models/sources.yml`: both raw tables declared with `dbt source freshness`
  (`warn_after: 2 days`, `error_after: 5 days`), using the business timestamp
  (`date_heure`, `time`) as `loaded_at_field` rather than dlt's own load
  timestamp -- we care whether the *data* is stale, not just whether the
  script ran recently. Ran `dbt source freshness`: both PASS, with
  `max_loaded_at` correctly reflecting the newest row in each table.
- `models/staging/stg_eco2mix_regional.sql` and `stg_weather_hourly.sql`:
  `try_cast` every measurement column to its real numeric type, no row
  removed. Verified `stg_eco2mix_regional.consommation_mw` ranges from 1387
  to 10425 (plausible French regional consumption in MW).
- **Found and fixed a real type mismatch**: `seeds/regions.csv`'s
  `code_insee_region` loaded as `int32` by `dbt seed`'s default CSV type
  inference (the column looks numeric), while every eco2mix/weather table
  has it as `varchar` (`'75'`, not `75`). Left alone, joining the seed to
  either staging model in step 5 would compare varchar to int. Fixed with a
  `+column_types: {code_insee_region: varchar}` override in `dbt_project.yml`
  under `seeds:`.
- `dbt run` builds both staging views: `Done. PASS=2 WARN=0 ERROR=0 SKIP=0`.
  `dbt seed` loads the 12 regions: `Done. PASS=1 ... TOTAL=1`.

### Why this matters for the four promises
- **Reproductible**: anyone cloning the repo gets the same `dev`/`prod`/`ci`
  split without editing a model -- `--target` is the only thing that changes.
- **Observable**: `dbt source freshness` is the mechanism the written SLO
  (step 13) will actually be measured against; wiring it to the business
  timestamp now means the number it reports is the one that matters.

### A question the individual exam could ask, answered here
**"Someone runs `dbt run` from a sub-folder instead of the repo root. What
happens, and how do you fix it?"** dbt looks for `dbt_project.yml` (and,
since it's not in `~/.dbt/`, `profiles.yml` via `DBT_PROFILES_DIR`) relative
to the current directory; from a subfolder it won't find either and fails
with `Could not find profile named 'energy_platform'` (or a "no
dbt_project.yml found" error even earlier). The fix is always the same:
`cd` back to the repo root before running dbt -- there's no flag that
replaces this, because dbt's whole project-discovery model assumes you run
it from there. This is exactly TP3's own troubleshooting note, we just hit
the version of it where `profiles.yml` isn't even in the default
`~/.dbt/` location, so the error shows up one step earlier.

---

## Step 5 — Rules, quarantine, marts in star (2026-11-12)

### What was done
- `models/intermediate/int_eco2mix_checked.sql`: first-match-wins
  `reject_reason` (TP3 pattern), with 5 rules: `missing_region`,
  `unknown_region` (checked against the `regions` seed, not a hard-coded
  list), `invalid_timestamp`, `missing_consumption`, `negative_consumption`,
  `duplicate_region_datetime`. The duplicate rule keeps the row with the
  **most recent** `_dlt_load_id` rather than TP3's "keep the first" -- a
  later load should supersede an earlier one for the same (region,
  timestamp), since a correction arriving later is more trustworthy than
  what we saw first, not less.
- `models/intermediate/int_energy_production_unpivoted.sql`: unpivots 6
  energy sources (thermique, nucleaire, eolien, solaire, hydraulique,
  bioenergies) into one row per region x timestamp x source, clean rows
  only. Storage/exchange columns (pompage, batteries, ech_physiques) are
  deliberately left out -- they aren't "production by source".
- `models/intermediate/int_consumption_hourly.sql`: averages eco2mix's
  15/30-min consumption up to the hour, to match weather's grain for the
  join.
- Seeds: `energy_sources.csv` (6 rows, `is_renewable` flag) alongside the
  existing `regions.csv`.
- Marts: `dim_region`, `dim_energy_source`, `dim_date` (built with
  `generate_series` bounded by the actual min/max `date_heure` in the data,
  not a hard-coded range, so it grows with the backfill), `fct_energy_production`
  (**incremental**, keyed on region+timestamp+source), `fct_consumption_weather`
  (joins the hourly-aggregated consumption to weather), `eco2mix_rejected`
  (quarantine). 11 models total, well past the "8 models, >=1 fct_, >=2 dim_"
  requirement.
- `dbt run` built all 11 on the first try, including the `generate_series`
  lateral join in `dim_date` and the incremental model.

### Proved the incremental model is actually incremental, not just a no-op
- Re-ran `dbt run --select fct_energy_production` with no new raw data:
  row count stayed at 13824 (2304 clean rows x 6 sources).
- Loaded one more day (2026-11-12) directly into raw (1104 new rows,
  bypassing the coupled ingest CLI since Open-Meteo's archive API correctly
  rejected the matching weather call -- its allowed range still ends at
  today, confirming the step-1 finding holds). Re-ran `dbt run`: fact table
  grew to 18438 rows. Reconciled by hand: 1104 new raw rows, 335 rejected
  (see below), 769 newly clean x 6 sources = 4614, and 13824 + 4614 = 18438
  exactly. A no-op run followed by a correctly-sized incremental run is what
  actually proves `is_incremental()` is doing its job, not just "the command
  didn't error".

### A real discovery, not a bug: the freshest hours of real-time data arrive empty
Debugging why 335 of the 1104 new rows were rejected led to finding that the
`eco2mix-regional-tr` dataset publishes a region/timestamp row **before**
its measurements exist -- every single measurement column was null for the
freshest ~7 hours of the day, not just `consommation`. Documented as an
addendum to ADR 0002, with a consequence for step 12: a daily orchestration
job that only ingests "new" dates would quarantine these rows once and never
revisit them, permanently losing data the API would have filled in a few
hours later. The fix (for step 12) is to re-ingest a short trailing window
each run, not just strictly new dates, so dlt's `merge` disposition can
upsert the real values once they appear.

Also relabeled the rule that catches this: it was originally one
`negative_consumption` reason covering both "null" and "actually negative" --
split into `missing_consumption` (null) and `negative_consumption` (truly
negative) once the data showed every single case was a null, not a negative
value. A quarantine table whose reason column lies about *why* a row was
rejected is worse than no quarantine table: the next person to read it (an
individual-exam grader, a teammate, future me) would draw the wrong
conclusion.

### A question the individual exam could ask, answered here
**"Why average consumption to the hour in `int_consumption_hourly` instead of
just picking one 15-minute reading per hour?"** Picking one reading (e.g.
the first) would silently throw away real variation within the hour and
make the choice of *which* reading arbitrary and undocumented -- exactly the
kind of hidden decision `CLAUDE.md`'s "never hide magic" rule exists to
avoid. Averaging is explicit about what happened to the data, and it's the
right aggregation for a quantity like power (MW) where the hourly figure we
actually want to compare against temperature is "how much was being drawn
on average that hour", not an arbitrary instant.

---

## Step 6 — dbt tests + docs (2026-11-12)

### What was done
- `models/marts/marts.yml`: generic tests on every mart -- `unique`/`not_null`
  on every primary key, `relationships` from both fact tables back to
  `dim_region` (and `fct_energy_production` to `dim_energy_source`), and
  `accepted_values` on two closed-list columns (`dim_energy_source.is_renewable`,
  `eco2mix_rejected.reject_reason`, listing the exact 6 reasons the model can
  produce -- this doubles as living documentation of the rule set). A
  description on every mart and every mart column.
- `data_tests/assert_fct_energy_production_unique_key.sql`: the built-in
  `unique` test only takes one column, but the fact table's real key is 3
  columns together, so this is a singular test (a `group by ... having
  count(*) > 1`, TP3 pattern).
- `data_tests/assert_reject_rate_below_20_percent.sql`: TP3's `check_reject_rate`
  translated to SQL, with a documented caveat -- the real-time dataset's
  freshest hours always show a temporary null spike (step 5's finding), so
  20% has to be wide enough to absorb one partial day's normal 9.8% without
  masking a real problem.
- `models/intermediate/int_eco2mix_checked.yml`: 2 dbt unit tests,
  `test_unknown_region_is_rejected` and
  `test_duplicate_region_datetime_keeps_latest_load`, following TP3's
  given/when/then shape exactly.
- `dbt docs generate`: builds cleanly; spot-checked `target/manifest.json`
  directly to confirm `fct_energy_production`'s `depends_on` correctly chains
  back through `int_energy_production_unpivoted`. (Didn't run `dbt docs serve`
  interactively in this session -- no browser attached -- but the artifact
  generation itself is the part that can actually fail, and it didn't.)
- `dbt build`: `Done. PASS=39 WARN=0 ERROR=0 SKIP=0` (11 models, 2 seeds, 24
  data tests, 2 unit tests).

### A real gotcha: unit tests need every ref() mocked, including seeds
First attempt at the unit tests failed to even compile:
`Unit_Test '...' depends on a node named 'regions' which was not found`.
`int_eco2mix_checked` references `{{ ref('regions') }}` (the seed) inside its
`unknown_region` check, and only `stg_eco2mix_regional` was given mock rows
in `given`. Unlike a plain `ref()` to a model that isn't being overridden
(which can fall back to the model's real build), **a `ref()` to a seed
inside a unit-tested model must also be given mock rows explicitly** -- it
doesn't fall back to the actual seed data in this dbt/dbt-duckdb version.
Fixed by adding a second `given.input: ref('regions')` with just the one row
(`'75'`) each test actually needs. This matters for *writing* correct unit
tests on any model that reads a seed, not just this one.

### Proved `dbt build` actually stops the chain (TP3's "Essayez" exercise, for real)
Temporarily deleted the `unknown_region` rule from `int_eco2mix_checked.sql`
and ran `dbt build`: `test_unknown_region_is_rejected` failed immediately
with a readable diff (`99,unknown_region→NULL`), and dbt `SKIP`ped every
downstream node -- `dim_date`, `eco2mix_rejected`,
`int_energy_production_unpivoted`, both fact tables, and all their tests (6
models + 10 tests skipped, exit code 1). Restored the rule, reran:
`PASS=39` again. This is the concrete mechanism behind "a red PR can't be
merged" (step 8): the failure is specific and immediate, not a vague
"something broke somewhere in 11 models".

### A question the individual exam could ask, answered here
**"Why does `eco2mix_rejected.reject_reason` get an `accepted_values` test
instead of just `not_null`?"** `not_null` alone would pass even if a typo
crept into one of the `case when` branches (e.g. `'uknown_region'`) -- it
only checks that *something* is there, not that it's one of the 6 reasons
the rule file can actually produce. `accepted_values` makes the YAML and the
SQL cross-check each other: if someone edits one list of reasons and forgets
the other, the test fails the next `dbt build`, not months later when a
dashboard filter silently stops matching a misspelled reason.

---

## Step 7 — Pytest + data contracts (2026-11-12)

### What was done
- Refactored `pipeline/sources/eco2mix.py`: extracted `_plan_fetches`, a pure
  function deciding which dataset(s) to query for a date range -- no network
  call -- out of `fetch_eco2mix_rows`. This is what made the cutover logic
  (ADR 0002) unit-testable without mocking `requests` at all.
- `tests/test_eco2mix_source.py` (4 tests): the 3 cutover cases (before,
  after, straddling) plus the exclusive-end-date edge case.
- `tests/test_schema.py` (6 tests): valid batch passes; the exact step-1
  finding (`eolien` mixed string/int) coerces cleanly; unknown region and
  implausible consumption are refused; weather's `strict=True` catches an
  extra column.
- `tests/test_ingest.py` (2 tests): `_validate_or_refuse` doesn't raise on a
  good batch, raises `SystemExit(1)` on a bad one.
- `python -m pytest`: **12 passed**. `ruff check .`: all clean.
- `contracts/eco2mix_regional.yaml`, `contracts/weather_hourly.yaml`: ODCS
  v3.2.0, each with a `ci` server pointing at a small CSV fixture, a named
  owner (`team.name`), a 10-year retention via `slaProperties`, and a
  `customProperties` entry stating explicitly that neither source carries
  personal data (region/city-level aggregates only, nothing about an
  individual).
- `tests/fixtures/eco2mix_sample.csv` (10 rows: 2 regions x 5 timestamps) and
  `weather_sample.csv` (6 rows: 2 regions x 3 hours), hand-built with round
  numbers so the reference total is easy to verify by hand: each eco2mix row
  sums to 900 MW across the 6 production sources (100+500+100+50+100+50),
  so 10 rows x 900 = **9000 MW total** once unpivoted.
- `datacontract lint`/`test --server ci` on both contracts: valid, 30 and 14
  checks respectively.
- **Proved the contract actually catches a broken shape** (TP4's "day 3"
  exercise, for real): temporarily renamed `consommation` to `consumption` in
  the fixture, ran `datacontract test` again -- red, exit 1, "Required
  column 'consommation' is missing". Restored the fixture, back to green.
- `tests/load_fixtures.py`: loads the two CSV fixtures into `ci.duckdb`'s
  `raw` schema, matching dlt's actual column types (timestamps as
  timestamps, every measurement column as text, including
  `eolien_terrestre`/`eolien_offshore` which aren't in the fixture at all but
  exist as null columns in the real raw table because of dlt's explicit
  type hints -- added as literal nulls here to match).
- `dbt build --target ci`: **PASS=39**, same as `dev`. Confirms the whole
  `stg_` -> `int_` -> marts chain works unchanged against a hand-built
  fixture, not just live API data.
- `report_md.py`: prints `fct_energy_production` as a Markdown table by
  energy source, with a grand total; exits 1 with `REGRESSION: ...` if the
  total doesn't match an expected value passed as an argument. Verified: `9000` passes (exit 0), `9999` fails (exit 1) with the exact TP4 message shape.

### Why this matters for the four promises
- **Reproductible**: `tests/load_fixtures.py` + `report_md.py` mean the
  whole pipeline can be exercised and checked against a known number without
  touching the live APIs at all -- this is what step 8's CI will actually
  run on every PR, in seconds, deterministically.
- **Fiable**: the contract and Pandera check different things on purpose
  (shape vs. plausibility), and now both have an automatic regression test
  proving they still catch what they're supposed to catch, not just that
  they exist.

### A gotcha avoided, not hit: the DuckDB-version trap from TP4
TP4 warns that installing `datacontract-cli` can downgrade DuckDB below 2.0,
breaking any `.duckdb` file written by a newer version. It didn't happen
here: `requirements.txt` already pinned `duckdb>=1.1,<2` back in step 2 (to
match `dbt-duckdb`'s own constraint), so there was nothing to downgrade.
`dev.duckdb` stayed readable (`fct_energy_production` still had its 18438
rows) immediately after installing `datacontract-cli`. Worth remembering:
a pin made for one reason (dbt-duckdb compatibility) quietly prevented an
unrelated problem two steps later.

### A question the individual exam could ask, answered here
**"Why does the data contract describe `eolien` as a plain number, when
`pipeline/schema.py`'s Pandera schema and the real raw table both treat it
as text?"** They're describing different things. The contract states what
the *supplier* is allowed to send -- and the supplier's own documentation
promises a number; the fact that the real-time dataset sometimes sends a
string is the exact kind of supplier inconsistency the contract exists to
catch (ADR 0002), not something to encode as "expected" in the contract
itself. Pandera and the raw table's forced-text columns are *our* defensive
reaction to that inconsistency once it's inside our pipeline -- a different
layer, solving a different problem, matching TP4's framing exactly: "the
contract describes the shape, not our rules for coping with a broken shape."

---

## Step 8 — CI quality gate (2026-11-12)

### What was done
- `.github/workflows/ci.yml`: 4 jobs -- `lint` (ruff), `gitleaks` (runs in
  parallel, doesn't block the others), `python-tests` (needs `lint`),
  `data-quality` (needs `python-tests`: both contracts, the fixtures
  through Pandera via `tests/validate_fixtures.py`, `python -m
  tests.load_fixtures`, `dbt build --target ci`, `report_md.py 9000 >>
  $GITHUB_STEP_SUMMARY`, and `run_results.json` uploaded as an artifact).
  Triggers on every pull request and on push to `main`.
- `.github/workflows/nightly.yml`: scheduled (05:00 UTC) + manual
  (`workflow_dispatch`), rebuilds from the same fixtures and runs `dbt docs
  generate`, uploading the docs as an artifact. **Scope note**: this
  rebuilds from the static CI fixtures, not live API data -- matching TP4's
  own nightly exactly, whose stated purpose is catching "a library upgrade
  breaks something", not refreshing production data. A real daily data
  refresh is Prefect's job (step 12), not this workflow.
- Enabled **branch protection on `main`** via the GitHub API: required
  status checks `lint`, `gitleaks`, `python-tests`, `data-quality`; no
  required PR-review approvals (solo project -- the self-review comment +
  green CI substitutes for a teammate's review, as noted in `CLAUDE.md`
  §6); force-push and branch deletion disabled.
- Watched the **actual** GitHub Actions run (not a local simulation) on the
  real PR for this branch: all 4 jobs green
  ([run 43277494795](https://github.com/ahmednouhAz/dataops-energy-platform/actions/runs/43277494795)).
  After merging, confirmed a fresh green run on `main` itself
  ([run 43277929611](https://github.com/ahmednouhAz/dataops-energy-platform/actions/runs/43277929611)).
  Manually triggered Nightly and confirmed the `dbt-docs` artifact actually
  contains `index.html`
  ([run 43278301751](https://github.com/ahmednouhAz/dataops-energy-platform/actions/runs/43278301751)).

### The two required red-PR demos (TP4 steps 7-8, done for real on GitHub, not simulated)
- **Supplier PR** ([PR #13](https://github.com/ahmednouhAz/dataops-energy-platform/pull/13),
  closed without merging): renamed `consommation` to `consumption` in the
  eco2mix fixture. Result: `lint`/`gitleaks`/`python-tests` green (no code
  changed), `data-quality` red at the contract step with "Required column
  'consommation' is missing", `mergeStateStatus: BLOCKED`.
- **Colleague PR** ([PR #14](https://github.com/ahmednouhAz/dataops-energy-platform/pull/14),
  closed without merging): widened the Pandera plausibility bound on
  `consommation` from `(0, 20000)` to `(-500, 999999999)`. Result:
  `lint`/`gitleaks` green, `python-tests` red
  (`test_implausible_consumption_is_refused` failed), `data-quality` never
  started (`needs:` chaining), `mergeStateStatus: BLOCKED`.
- Both demos were verified against the real `mergeStateStatus` field via
  `gh pr view --json mergeable,mergeStateStatus`, not just "the checks look
  red" -- the thing that actually matters is that GitHub itself, not just a
  human reading the Checks tab, refuses the merge.

### Why this matters for the four promises
- **Fiable**: the two demos prove the gate catches *both* kinds of break
  the brief names -- a data change (supplier) and a code change
  (colleague) -- and that recovery is just closing the PR; `main` was never
  at risk because the change never merged.
- **Reproductible**: anyone cloning the repo gets the same required checks
  the moment they open a PR; nothing about the gate depends on a human
  remembering to run something locally first.

### A question the individual exam could ask, answered here
**"The CI is red on a PR that touches `models/marts/`. Where do you look
first, and why?"** `needs:` tells you where to look before reading a single
log line: if `python-tests` is red, `data-quality` never ran at all, so the
problem is in Python code or a dbt unit test's fixture rows, not the SQL
itself. If `python-tests` is green but `data-quality` is red, the problem is
either the contract (shape), Pandera (batch plausibility), or an actual dbt
model/test -- and the job's own step names (`Data contracts on the CI
samples` vs. `dbt build`) say which one failed before you even open the
full log.

---

## Step 9 — DVC (2026-11-12)

### What was done
- Installed `dvc[s3]` (the S3 extra now, not later -- MinIO is S3-compatible,
  so step 11's migration is just changing one line in `.dvc/config`, no new
  dependency to add then).
- `scripts/build_reference_dataset.py`: pulls a **fixed** historical week
  (2026-09-01 to 2026-09-07) from both real APIs and saves it as CSV under
  `data/reference/`. Deliberately not "the last 7 days" -- a reference
  dataset has to produce the exact same file every time it's rebuilt, which
  a sliding window can't guarantee. Got exactly 8064 eco2mix rows (7 days x
  96 x 12 regions) and 2016 weather rows (7 x 24 x 12), confirming 0 nulls
  in `consommation` -- this window is safely past the freshest-hours null
  gap from the step 5/ADR 0002 addendum.
- `dvc init`, `dvc add data/reference`, `dvc remote add -d storage
  ../dataops-dvc-storage` (a local folder, sibling to the repo, same choice
  TP2 makes before a shared remote exists), `dvc push`.
- `docs/adr/0003-dvc-remote.md`: explains why `data/reference/` is separate
  from the tiny `tests/fixtures/*.csv` (which TP4 explicitly says belongs in
  plain Git, not DVC) and from the full backfill (step 10, warehouse-only,
  never a tracked file), why the date range is fixed, and the known
  limitation that `dvc pull` only works on this machine until the remote
  moves to MinIO (step 11).
- **Proved the actual recovery mechanic**, not just that the commands ran:
  deleted `data/reference/` *and* `.dvc/cache` (simulating a genuinely fresh
  clone, not just a checkout), ran `dvc pull`: `3 files fetched and 2 files
  added`, both CSVs back with their exact original line counts, `dvc
  status` reporting clean.

### Why this matters for the four promises
- **Reproductible**: this is the literal mechanism behind "clone the repo
  and get the same data" for anything too big for Git -- proven by
  deliberately destroying both the working copy and the cache, not just
  trusting the tutorial said it would work.

### A question the individual exam could ask, answered here
**"Why isn't `tests/fixtures/eco2mix_sample.csv` under DVC too, since it's
also data?"** Size and volatility, not "is it data". DVC's whole value is
versioning something too big or too fast-changing to live comfortably in
Git's history; a 10-row fixture that almost never changes is exactly what
Git handles fine on its own, and TP4 says so explicitly. Putting it under
DVC anyway would mean the CI job needs a `dvc pull` step just to get a file
smaller than this sentence -- extra moving parts for no benefit. `data/reference/`
earns DVC because it's 1.6 MB, built from two live API calls, and only
useful at a size nobody wants sitting in `git log` forever.

## Step 10 — Backfill (2026-11-12)

### What was done
- `pipeline/sources/eco2mix.py::fetch_definitive_backfill_rows`: bulk-fetch
  via Opendatasoft's `/exports/csv` endpoint, no pagination cap (unlike
  `/records`'s 100-rows/page, which would need ~29,000 requests for the
  full history). `pipeline/backfill.py` chunks the range one calendar year
  at a time, 2013-01-01 to the cutover date (2026-08-31).
- `pipeline/http_utils.py::get_with_retries`: a real `ConnectionError`
  (connection reset) killed the first full run mid-backfill; wrapped every
  HTTP call in both sources with 3 retries.
- `_normalize_backfill_row`: the CSV export uses two different missing-value
  placeholders (`""` and, found in real 2013 `eolien` data, a literal `-`)
  where the JSON `/records` endpoint just sends `null`. Pandera correctly
  *refused* the first 2013 chunk over this (a `str`/`int` comparison
  error) rather than silently loading bad data -- the validation did
  exactly its job, and the fix was in the fetch code, not in Pandera.
- **Found a real performance bug during the first full run**: using
  `write_disposition="merge"` (same as daily ingestion) made every chunk
  slower than the last -- 1m42s for year 1, 8m27s by year 10 -- because
  `merge` re-scans the whole destination table on every load. Killed the
  run after 50 minutes (10/14 years) rather than let it keep degrading.
  Fixed with an explicit delete-then-append per chunk instead
  (`_delete_existing_chunk` + `write_disposition="append"`): one year
  dropped from 8m27s to 93.6s.
- **Found a second, subtler bug by testing idempotency**: re-running the
  2015 chunk changed the row count (+24), which should be impossible if
  the operation is truly idempotent. Traced to France's DST spring-forward
  transition -- the source API genuinely emits two rows for the same
  `(region, timestamp)` that one day a year. The *old* `merge`-based loads
  (years 2013-2022) had been silently swallowing this duplicate at
  raw-load time, hiding it from `int_eco2mix_checked`'s quarantine rule,
  while the new delete-then-append approach preserves it and lets dbt
  catch it transparently -- an inconsistency across years that contradicts
  "raw = untouched." Fixed by reloading **all 14 years** with the
  corrected approach, and by adding `_dlt_id desc` as a tie-breaker in
  `int_eco2mix_checked.sql`'s dedup rule (both duplicate rows share one
  `_dlt_load_id`, so without a secondary key which row survives was
  undefined, not just unlikely to matter).
- **Found a third issue reconciling the rebuilt fact table**: after
  `dbt build --full-refresh`, 701,286 nulls failed `fct_energy_production`'s
  `not_null` test on `production_mw`. Traced to 5 of 12 regions having zero
  nuclear capacity -- a legitimate "not applicable," not a quality defect.
  Fixed in `int_energy_production_unpivoted.sql` by filtering out null
  `production_mw` after the unpivot instead of quarantining or forcing a
  misleading `0`.
- Also learned (the hard way, via a failed `query.py` call) that an
  incremental model's `is_incremental()` filter only looks *forward*
  (`date_heure > max seen so far`), so it silently ignores a backfill that
  adds data *older* than what's already there -- needs `dbt build
  --full-refresh` after any backfill, not a plain `dbt build`.
- See `docs/adr/0004-backfill-approach.md` for the full decision record.

### Verification
- `raw.eco2mix_regional`: 2,877,672 rows, 2,877,336 distinct
  `(code_insee_region, date_heure)` keys -- the 336-row gap is exactly
  14 years x 24 rows (12 regions x 2 DST-duplicate rows each), confirmed
  uniform across every single year.
- `dbt build --full-refresh`: `PASS=39 WARN=0 ERROR=0 SKIP=0`.
  `fct_energy_production`: 16,560,648 rows (>= 1,000,000 requirement met).
- **Idempotency proved directly**: counted `raw.eco2mix_regional` rows for
  2015 (210,240) and the global total/distinct-key counts, re-ran the 2015
  chunk a second time, counted again -- identical before and after.

### Why this matters for the four promises
- **Reliable**: two of the three bugs found here (the silent `merge`
  dedup, the nuclear-null false alarm) would have published a wrong number
  with no error anywhere -- the kind of mistake that only idempotency
  testing and cross-checking row counts against reality (which regions
  have nuclear plants?) catches.
- **Reproductible**: the backfill is a parametrized script
  (`--start-date`/`--end-date`), not a one-off manual sequence of API
  calls -- anyone can rebuild the full history with one command.

### A question the individual exam could ask, answered here
**"You ran the same backfill chunk twice and the row count changed. Is
that a bug in your idempotency logic?"** No -- it was a bug in what the
*old* loads had done, not the re-run itself. The re-run (delete-then-append)
behaved correctly both times; what changed was that the *first* run under
the new code preserved a duplicate the *previous* `merge`-based load had
been silently eating. The lesson: idempotency means "running this
operation twice gives the same result as running it once" -- it does not
mean "today's result must match whatever a differently-built pipeline
produced yesterday." Catching the mismatch required comparing counts
before/after a re-run, which is exactly why that proof is part of this
step's deliverable.

## Step 11 — Docker Compose (2026-11-12)

### What was done
- `Dockerfile`: `python:3.12.7-slim-bookworm` + `git` (dbt shells out to it
  even with zero packages installed -- `dbt debug` reported it as a failed
  check without this) + `requirements.txt`. Stays alive with `sleep
  infinity` -- no long-running process exists yet, Prefect flows are step
  12 -- so it can be `docker compose exec`'d into.
- `docker-compose.yml`: `minio` (object storage), `minio-setup` (one-shot
  bucket creation, exits), `prefect-server` (server only, no flows
  registered yet), `worker` (our image, bind-mounts the real repo over
  `/app` so it always runs today's code against the host's own
  `dev.duckdb`, no rebuild needed to pick up a code change).
- `.env.example` (MinIO credentials, `DUCKDB_PATH`, `PREFECT_API_URL`),
  `.env` gitignored (already was).
- Migrated DVC's `storage` remote from the local-folder stand-in (ADR
  0003) to this MinIO instance.

### A real problem CLAUDE.md's plan couldn't have anticipated: the free MinIO image is gone
`docker pull minio/minio` -- the standard choice in every MinIO tutorial,
including the one this course's materials assumed -- returns `pull access
denied`. Checked both Docker Hub and its `quay.io` mirror directly (not
just read about it): both refuse the pull. MinIO stopped publishing the
free Community Edition container image to either registry on 2025-10-23.
Found a working free alternative, **Chainguard's `cgr.dev/chainguard/minio`**,
and verified it directly before committing to it:
- Only ships a `latest` tag on the free tier -- no versioned tags to pin
  to, which looks like it breaks "pin image versions." Pinned by **digest**
  instead (`@sha256:...`), which is actually a *stronger* guarantee than a
  version tag (a tag can be moved to a different build later; a digest
  never can).
- Minimal image, no `curl`/`wget` for the usual healthcheck pattern. Used
  bash's `/dev/tcp` pseudo-device (`exec 3<>/dev/tcp/localhost/9000`) to
  open a raw TCP check with no extra binary -- tested directly against the
  image first, not assumed to work.
- Bundles `mc` (the MinIO client), so `minio-setup` reuses the same image
  with a different entrypoint instead of needing a second image pull
  (`minio/mc` also disappeared the same way).
- Runs as a non-root user (UID 65532) -- a named Docker volume for `/data`
  avoids the file-permission problem a bind-mounted host folder would hit,
  because Docker initializes a fresh named volume's ownership from the
  image itself.
- See `docs/adr/0005-docker-compose.md` for the full record, including
  the alternatives checked and rejected (`bitnami/minio` also lost its
  free maintained tags, for the same underlying reason, around the same
  time).

### A quirk found, deliberately not "fixed"
`ruff check .` run inside the worker container reports 20 `EXE002` errors
("executable but no shebang") that never show up on the host or in CI.
Cause: Docker Desktop's Windows bind-mount translation marks every file
executable (NTFS has no POSIX exec bit to translate from), which a real
Linux git checkout -- including GitHub Actions' -- never does, since mode
bits there come from git's own index. Left the rule alone rather than
relaxing it for everyone just to paper over a Windows-specific
side-effect: lint still runs on the host/CI, where it's accurate; the
container is for running the actual pipeline/dbt/pytest, not for linting.

### Verification
- `docker compose up -d --build`: `minio` reports `(healthy)`,
  `minio-setup` exits 0 with `Bucket created successfully`,
  `prefect-server` and `worker` both `Up`.
- `docker compose exec worker python -m pytest -q`: 15 passed.
- `docker compose exec worker dbt debug`: all checks passed.
- `docker compose exec worker dbt build --select dim_region`: PASS=6,
  against the exact same `dev.duckdb` the host's own `dbt build` uses --
  proves the bind mount, not a second copy of the warehouse.
- From inside `worker`, `http://prefect-server:4200/api/health` → HTTP 200.
- DVC/MinIO migration: `dvc push`, then deleted `data/reference/` *and*
  `.dvc/cache`, `dvc pull` restored both files with their exact original
  line counts (8065 and 2017, header included) -- same recovery proof as
  step 9, now against the real remote instead of the local-folder
  stand-in.

### Why this matters for the four promises
- **Reproductible**: `git clone` + `docker compose up` + `docker compose
  exec worker pytest`/`dbt build` now needs nothing installed on the host
  except Docker itself -- proved by actually running the test suite and a
  dbt model from inside the container, not just by the containers reporting
  "Up."
- **Automatic**: step 12 (Prefect flows) now has a server to register
  against; this step is deliberately "the plumbing," not the automation
  itself.

### A question the individual exam could ask, answered here
**"Why pin a Docker image by digest instead of a version tag?"** Normally
you'd pin a tag (`minio:RELEASE.2024-...`) because it's human-readable and
"usually" stable. Here the *only* free tag available is `latest`, which by
definition can point to a different build tomorrow -- the opposite of
reproducible. A digest (`@sha256:...`) is the hash of the actual image
content: it is physically impossible for it to resolve to a different
build later, even if `latest` moves on. It's less readable, but strictly
more reproducible, which is the property that actually matters for "my
platform builds the same way every time."

## Step 12 — Orchestration with Prefect (2026-11-13)

### What was done
- `flows/daily.py`: `ingest -> dbt build --target prod -> publish`, each
  step a Prefect `@task` with its own retries, inside one `@flow`.
  `python -m flows.daily --serve` registers a daily 06:00 UTC schedule
  (`flow.serve(cron=...)`) and keeps running to execute it -- this is now
  `docker-compose.yml`'s `worker` service's default command, so the
  schedule is live as soon as `docker compose up` is, no extra step.
- `flows/backfill_flow.py`: reuses `pipeline/backfill.py`'s already
  -proved chunk logic (step 10) with each year chunk as a retried task,
  invoked on demand, not scheduled -- a backfill is a one-off with a
  specific range, not a recurring job.
- `flows/alerts.py`: one `requests.post` to a Discord webhook, as both
  flows' `on_failure` hook. Logs instead of sending when
  `DISCORD_WEBHOOK_URL` isn't set, so the flows behave the same with or
  without a real Discord server wired up -- only the student can create
  that webhook (it's tied to their own Discord server), so it's never
  filled in by default.
- Pinned the Prefect **server** image to the exact same version as the
  **client** library (`prefecthq/prefect:3.9.2-python3.12` /
  `prefect==3.9.2`), after the client warned about talking to an older
  server -- the only exact (not range) pin in `requirements.txt`, because
  this is the one dependency with a server half that has to match.
- Pulled `run_ingest` out of `pipeline/ingest.py`'s `main()` so the daily
  flow's task can call it directly (no subprocess, structured return
  value instead of scraped stdout); `main()` is now a thin CLI wrapper
  around the same function.

### A real bug, found only by actually running the flow once
The first real run of `flows.daily` (live APIs, not a fixture) failed:
Open-Meteo returned `400 Bad Request` for a date one day in the future.
Cause: eco2mix's API treats `end_date` as exclusive, Open-Meteo's treats
it as inclusive, and `run_ingest` was passing one shared `end_date` to
both -- a latent inconsistency since step 2 that no caller had ever
actually exercised, because every existing call (always by hand) happened
to pick values that avoided it. `flows/daily.py`'s automatic "trailing
window ending tomorrow, to catch today" default was the first caller to
really ask for data through *today* from both sources in the same call.
`pipeline/backfill.py` had already solved the identical problem in step
10 (`_load_weather_chunk` subtracts a day before calling weather); applied
the same fix inside `run_ingest` itself, so the CLI gets the correction
too, not just the new flow. Confirmed fixed by re-running: both sources
fetched cleanly, `dbt build --target prod` reached PASS=39.

### A false alarm, not a pipeline bug
A backfill-flow smoke test failed with a cryptic dlt configuration error
on a path (`/tmp/test_backfill.duckdb`) that looked completely normal.
Cause: Git Bash on Windows silently mangles absolute POSIX paths passed
through `docker compose exec -e VAR=...` -- the exact same class of
problem ADR 0005 already hit with `--entrypoint /bin/sh`. A relative path
worked immediately, no code change needed. Worth remembering for the
exam: a weird error while testing isn't automatically a bug in the code
under test.

### Verification
- `docker compose exec worker python -m flows.daily`: ingested 3408
  eco2mix + 864 weather rows, `dbt build --target prod` PASS=39,
  `prod.duckdb` published to `serving.duckdb` (confirmed same byte size).
- The pre-fix failed run is recorded as `FAILED` in Prefect's own history
  (`/api/flow_runs/filter`), and the Discord hook logged correctly with no
  webhook configured -- the alert path really runs on a real failure.
- `docker compose up -d worker`: logs confirm the flow "is being served
  and polling for scheduled runs"; `/api/deployments/<id>` confirms
  `schedule.cron == "0 6 * * *"`, `active: true`.
- `tests/test_alerts.py` (2 new tests): no webhook -> `requests.post`
  never called; webhook set -> called once with the exact expected
  URL/payload. `ruff check .` clean, 17/17 pytest passing.

### Why this matters for the four promises
- **Automatic**: this is the step where "a human has to remember to run
  this" actually stops being true -- the schedule lives inside the
  container that `docker compose up` already starts.
- **Observable**: every task attempt (including retries) and every flow
  run's final state are queryable facts now (Prefect's API/UI), not just
  whatever happened to be printed to a terminal that's since been closed.

### A question the individual exam could ask, answered here
**"The daily flow is scheduled for 06:00 UTC and it's 06:05 and nothing
ran -- what do you check, in order?"** (1) Is the `worker` container even
up (`docker compose ps`) -- if it crashed, no process is polling for
scheduled runs at all. (2) Is the schedule actually `active` on the
deployment (`/api/deployments/<id>`) -- `flow.serve()` only registers it
once, at startup; a code change to the cron string needs a restart to
take effect. (3) Prefect's own UI/API flow-run history for that
deployment -- a run that's `Late` or `Crashed` means the scheduler fired
correctly and something else went wrong (check the task logs next), which
is a completely different problem from the scheduler never firing at all.

## Step 13 — Observability (2026-11-14)

### What was done
- `flows/metrics.py`: pushes 6 gauges (duration, rows loaded per source,
  rows rejected, reject rate, freshness hours, run success) to a
  Prometheus Pushgateway at the end of every daily run -- success *and*
  failure, via a `try/finally` in `daily_flow` (`flows/daily.py`).
- `docker-compose.yml`: added `pushgateway`, `prometheus` (scrapes the
  gateway), `grafana` (one provisioned datasource, one dashboard, one
  Discord contact point, two alert rules --
  `monitoring/grafana/provisioning/`, `monitoring/grafana/dashboards/`).
- `docs/slo.md`: the written freshness SLO -- 30 hours, derived from the
  06:00 UTC schedule plus a 6-hour buffer, with the reasoning spelled out.
- **Deliberately two separate alert paths, not one**: Prefect's
  `on_failure` hook (step 12) fires when a flow *run* crashes; Grafana's
  alert rules (this step) fire on the *published data's state*
  (freshness > 30h, reject rate > 20%) -- a signal the orchestrator
  literally can't see on its own, e.g. the whole `worker` container not
  running at all, so there's no flow run to even fail.

### Three real bugs, found only by actually pushing a real run's metrics
- **Grafana crash-looped on an empty `DISCORD_WEBHOOK_URL`.** Its Discord
  contact point validation refuses to start at all with an empty URL
  (`could not find webhook url property in settings`) -- a much harsher
  failure mode than `flows/alerts.py`'s own graceful "log instead of
  send" for the exact same "not configured yet" situation. Fixed with a
  Docker Compose default-value fallback
  (`${DISCORD_WEBHOOK_URL:-https://...placeholder}`) scoped to the
  `grafana` service only, so the worker's already-correct empty-by-default
  behavior didn't need to change.
- **`Duplicated timeseries in CollectorRegistry` on the first real
  push.** Built two separate `Gauge(...)` objects with the same metric
  name (one per source) instead of one `Gauge` with two `.labels()`
  calls -- `prometheus_client` registers a name at construction time, so
  the second object collided. One-line fix: construct once, label twice.
- **`Binder Error: Catalog "prod" does not exist!` -- on views only,
  never on tables, same file, same connection style.** `dbt build
  --target prod` compiles a view's cross-schema references (e.g.
  `stg_eco2mix_regional`'s `source()` call) as `prod.raw....`, where
  `prod` is the dbt **target name**, not anything derived from the file
  path. `publish_task`'s raw file copy carries that compiled SQL along
  with it; a plain `duckdb.connect(serving_duckdb_path)` has no catalog
  literally named `prod`, so views break while tables (no stored
  cross-catalog reference) read back fine -- which is exactly what made
  this confusing to diagnose at first. Fixed by attaching the file under
  the matching alias instead: `attach '<path>' as prod (read_only)` then
  `use prod`, the same thing dbt-duckdb does internally.

### Verification
- `docker compose up -d grafana`: stays up with the fallback (previously
  `Exited (1)` without it).
- Dashboard, alert rules, and contact point all confirmed loaded via
  Grafana's own provisioning API
  (`/api/search`, `/api/v1/provisioning/alert-rules`,
  `/api/v1/provisioning/contact-points`).
- Ran `flows.daily` for real: metrics pushed cleanly, then confirmed via
  Prometheus's query API with real numbers -- freshness ≈ 0.36h, rows
  loaded 3124 (eco2mix) / 864 (weather), reject rate ≈ 0.127.
- `tests/test_metrics.py` (5 new unit tests, tiny hand-built DuckDB
  fixtures): missing file, empty table, and a known 2/10 reject-rate
  fixture all give the expected answer. `ruff check .` clean, 22 pytest
  tests passing.

### Why this matters for the four promises
- **Observable**: this is the step that actually delivers the promise's
  own wording -- "we always know whether data is fresh, complete and
  correct" -- as a number you can watch over time, not just a pass/fail
  at build time.
- **Reliable**: the freshness SLO catches a failure mode step 12's own
  alerting structurally cannot: the orchestrator container itself not
  running. A flow that never got a chance to fail can't trigger an
  `on_failure` hook; a metric that simply stops updating can still trigger
  an alert.

### A question the individual exam could ask, answered here
**"Grafana shows the freshness panel stuck at the same value for two
days. Prefect's UI shows no failed runs at all. What's going on?"** Check
whether there have been any runs *at all* in that window, not just
whether any failed -- `docker compose ps worker` and the deployment's
flow-run history. A container that crashed or was never started has zero
runs, which looks identical to "every run technically succeeded" from a
metrics-only view, but means nothing has refreshed `serving.duckdb` at
all -- exactly the gap this step's SLO alert exists to catch, since
Prefect's own `on_failure` hook never had anything to fire on.

## Step 14 — Dashboard (2026-11-14)

### What was done
- Tried **Evidence** first (the plan's other option, and the one that
  seemed like the obvious fit for a DuckDB-first project): scaffolded a
  real project (`npx degit evidence-dev/template`) and read its current
  self-host docs directly, rather than trusting what I remembered about
  it. Found it had moved to a login-gated cloud product (Evidence
  Studio) for the scaffolded template, and that the still-open-source
  core's self-host connector list has no local-DuckDB-file option at
  all (Snowflake, Postgres, BigQuery, ClickHouse, MotherDuck cloud...
  but not a plain `.duckdb` file). Documented the exact finding and
  pivoted -- see ADR 0008.
- **Metabase** instead, self-hosted via the community
  `ghcr.io/motherduckdb/metabase-duckdb` image (official Metabase has no
  DuckDB driver of its own). `docker-compose.yml` adds `metabase` (port
  3001 -- 3000 was already Grafana's) and a one-shot `metabase-setup`
  job.
- `scripts/setup_metabase.py`: calls Metabase's own REST API (found by
  testing the calls directly with `curl` first, not guessed) to create
  the admin user, add the DuckDB connection pointed at
  `SERVING_DUCKDB_PATH`, and build 3 native-SQL cards + 1 dashboard
  answering `docs/business_questions.md`'s 3 questions. Idempotent:
  every step checks for an existing match before creating one.
- `models/exposures.yml`: declares the dashboard as a dbt exposure,
  `depends_on` naming exactly the 4 marts it reads.
- A real model change the dashboard needed: business question 3 (which
  regions depend on imports at their consumption peak) needs
  `ech_physiques_mw` alongside consumption at the same region/hour grain
  -- not in any existing mart. Added `ech_physiques_mw_avg` to
  `int_consumption_hourly` and `fct_consumption_weather` rather than
  inventing a new mart for one column at a grain that already exists.

### Two real problems, found only by actually running it
- **`AccessDeniedException` on Metabase's own app database.** Mounted a
  fresh named volume at `/metabase-data` -- a path I invented, not one
  the image's Dockerfile ever created -- so Docker couldn't infer
  correct ownership for it, and the non-root `metabase` user couldn't
  write there. Metabase crashed before even reaching the setup wizard.
  Fixed by mounting the volume at `/home/metabase` instead (the image's
  own working directory, already correctly owned) -- the same root
  cause as step 11's MinIO non-root-UID finding, a different image.
- **Port 3000 collision with Grafana** (step 13). Mapped Metabase to
  host port 3001 instead.

### Verification
- `docker compose up -d metabase metabase-setup` on a wiped
  `metabase-data` volume: Metabase `(healthy)`, setup job exits with
  `Dashboard ready: http://metabase:3000/dashboard/2`.
- Re-ran the setup job a second time: identical dashboard id, no
  duplicate database/cards/dashboard -- idempotency proved directly.
- All 3 cards executed via `/api/card/<id>/query`: `status: completed`,
  real rows (e.g. question 3's query correctly returning each region's
  actual peak hour, peak MW, and import/export role at that hour).
- `dbt build`: PASS=39/40 (including the new exposure) with the new
  `ech_physiques_mw_avg` column.

### Why this matters for the four promises
- **Reproductible**: Evidence looked like the "obviously correct"
  choice going in; actually trying it instead of assuming is what
  caught the login/connector problem before it became load-bearing. The
  final Metabase setup needs zero manual clicking on a clean machine,
  same bar as every other service in this stack.
- **Reliable**: the dashboard reads the *published* copy
  (`serving.duckdb`), never the file dbt is actively writing to -- the
  same write-audit-publish split (step 11/12/13) applied to its fourth
  reader now.

### A question the individual exam could ask, answered here
**"The teacher adds a 4th business question at the defense. Walk through
what changes."** If the new question is answerable from existing marts:
add one more entry to `CARDS` in `scripts/setup_metabase.py`
(name/query/display), re-run `docker compose up` (or
`docker compose run --rm metabase-setup`) -- idempotent, so it only adds
the one new card and appends it to the dashboard, nothing else moves.
If it needs a column no mart has yet (like question 3 needed
`ech_physiques_mw_avg`): that's a dbt model change first (which mart, or
a new one, and why), `dbt build`, *then* the card. The distinction
matters: a dashboard change is cheap and reversible; a model change
needs the same scrutiny (tests, description, a reason not to misuse an
existing mart) as any other step in this project.

## Step 15 — CD: GHCR releases and rollback (2026-11-14)

### What was done
- `.github/workflows/release.yml`: on a `v*` tag push (never a plain
  merge -- publishing is a deliberate act), builds the pipeline image
  and pushes it to GHCR tagged with the version and `latest`.
- `docker-compose.prod.yml`: an override swapping `worker`/
  `metabase-setup` to pull a specific `RELEASE_TAG` instead of building
  locally.
- `docs/rollback.md` + `docs/adr/0009-release-and-rollback.md`: the
  documented procedure, plus everything found while actually running it
  end to end for real -- not simulated.
- "Dev vs prod environments" was already satisfied by steps 4/11/12
  (dbt's `dev`/`prod`/`ci` targets, `PROD_DUCKDB_PATH`/
  `SERVING_DUCKDB_PATH` vs. the interactive `DUCKDB_PATH`) -- nothing
  new needed here.

### Three real things found only by actually doing a release and a rollback
- **Compose can't unset a key from an override file.** Tried removing
  the dev-mode bind mount (`.:/app`) for a "true" prod topology where an
  image rollback would roll back code too, not just dependencies.
  `build: null` and an empty-list `volumes:` override were both tested
  and confirmed (via `docker compose ... config`) to be silently
  ignored -- Compose keeps the base file's value regardless. The
  Compose Specification's actual mechanism for this is the `!reset` YAML
  tag (`volumes: !reset []`), which *did* work -- but using it properly
  would have meant a second shared volume and a second set of data-path
  env vars just for the prod case, real new infrastructure for a
  project that still deploys to "one desktop running Docker Compose."
  Documented the honest, simpler tradeoff instead: this rollback rolls
  back the image's baked *dependencies*; rolling back the *code* too
  needs a second, explicit `git checkout <tag>` on the host, because the
  bind mount means the container always runs whatever the host's
  working tree has checked out.
- **The git tag and the published image tag don't match.** Pushed
  `v0.1.0`, `release.yml` reported success, then `docker pull
  ghcr.io/.../dataops-energy-platform:v0.1.0` failed with `manifest
  unknown`. Checked the job's own logs rather than guessing:
  `docker/metadata-action`'s semver pattern strips the leading `v` --
  the image is actually `:0.1.0`. Not a bug (bare-number image tags are
  the normal Docker convention), but a real trap documented explicitly
  now rather than left for the next person to rediscover the same way.
- **A "trivial" dependency bump can resolve to the exact same installed
  version.** Bumped `ruff>=0.6` to `ruff>=0.7,<1` to produce a
  genuinely different `v0.1.1` image for the rollback test -- but both
  ranges allowed the same latest release (`0.17.5`) at build time, so
  `pip show ruff` gave an identical answer in both images. The rollback
  *mechanism* is still proven (the running container's image reference
  and its `org.opencontainers.image.revision` label both correctly
  matched the older release, differing from the newer one), but it's a
  reminder that "I changed a version constraint" doesn't always mean "a
  different version actually got installed" -- check the resolved
  version, not just the written constraint, when that distinction
  matters.

### Verification
- `v0.1.0` tagged and pushed: published and pulled successfully.
- `v0.1.1` tagged and pushed (after the real dependency bump): published
  as `:0.1.1`, `:latest` moved to the same digest.
- Rolled back to `0.1.0` for real: `docker inspect dataops-worker-1
  --format '{{.Config.Image}}'` → the `0.1.0` image; its
  `org.opencontainers.image.revision` label matched `v0.1.0`'s exact
  commit SHA, differing from `v0.1.1`'s -- two genuinely different
  builds, confirmed, not assumed from the tag name alone.
- Restored the worker to normal dev mode afterward and confirmed it was
  back on the locally-built image.

### Why this matters for the four promises
- **Reproductible**: "rollback" is now a documented, two-command
  procedure with a verification step that checks the actual running
  container, not a hope that `docker compose up` did the right thing.
- **Reliable**: writing down the bind-mount limitation *honestly*,
  instead of building a more complex topology to paper over it, is
  itself a reliability property -- the next person (teacher, jury,
  future me) won't be surprised by what a rollback actually does and
  doesn't cover.

### A question the individual exam could ask, answered here
**"You rolled back to v0.1.0 but the bug is still there. Why?"** Because
the bug was in the *application code*, and this project's `worker`
service bind-mounts the live repo for dev convenience (ADR 0005) -- the
image rollback only rolled back baked *dependencies*. Fixing a code bug
means `git checkout v0.1.0` (or whichever tag) on the host as well, not
just redeploying an older image. Confusing "which artifact actually
changed" is exactly the kind of mistake that costs the most time during
a live incident -- which is why `docs/rollback.md` spells this out
explicitly rather than leaving it to be rediscovered under pressure.

## Step 16 — Governance (2026-11-14)

### What was done
- Most of this checklist was already satisfied by earlier steps, not
  new work here: `contracts/*.yaml` have had owner + 10-year retention
  + a `contains_pii: false`/`pii_note` statement since step 7; gitleaks
  has run in CI since step 8; lineage has been documented via
  `dbt docs generate` since step 6, and now includes the step-14
  dashboard exposure too.
- What was actually new: `macros/mask_pii.sql` (two techniques --
  SHA-256 pseudonymization, and partial redaction keeping the last N
  characters) plus `models/governance/demo_pii_masking.sql` and 2 dbt
  unit tests proving it works on a known input, even though nothing in
  this warehouse is personal data and the macro is applied to nothing
  real. CLAUDE.md's own checklist asks for exactly this: "document it
  explicitly in the contracts [already done], and show the masking
  mechanism anyway, e.g. a macro."
- Verified DuckDB's `sha256()`/`repeat()`/`right()`/`greatest()`
  functions directly before writing the macro, same empirical habit as
  every other step this session -- confirmed the macro's SQL would
  actually run before building a model and tests around it.

### Verification
- `dbt build --select demo_pii_masking`: `PASS=3` (the view + both unit
  tests), each unit test checking an exact, independently-computed
  expected value, not just "it ran without erroring."
- `dbt build` (full project): `PASS=42/43` (the 1 exposure is a no-op
  by design), no regressions from adding the new `governance/` model
  path.
- `dbt docs generate`: completes, catalog includes the new model.

### Why this matters for the four promises
- **Reliable**: a governance claim that isn't backed by anything
  runnable ("we'd mask it if we needed to") is exactly the kind of
  claim that falls apart the moment someone asks to see it work. This
  one doesn't, because it's a real macro with a real test, not a
  sentence in a doc.

### A question the individual exam could ask, answered here
**"The teacher adds a new source next month with a real email column.
What changes?"** Three things, in order: (1) the new source's
`contracts/<source>.yaml` gets `contains_pii: true` and a real
`pii_note` (not `false`, which would now be a lie); (2) wherever that
column becomes visible beyond the raw layer (a staging or mart model --
never raw itself, which stays untouched per CLAUDE.md section 4),
wrap it with `{{ mask_pii(...) }}`, choosing hash vs. partial redaction
based on whether anything downstream needs to recognize *which* record
it is; (3) add a unit test pinning the new column's expected masked
output, same pattern `models/governance/governance.yml` already
demonstrates -- the mechanism from this step gets reused, not
reinvented.

## Step 17 — Docs & game day (2026-11-14)

### What was done
- `README.md` (what the platform is, one-command run instructions,
  service URLs, links to every other doc), `docs/architecture.md` (a
  Mermaid diagram plus the reasoning already scattered across
  `docs/adr/`, now shown as one picture), `docs/runbook.md` (a
  diagnose-fix-verify procedure for each of the 3 alerts that actually
  exist).
- A real game day: 3 scenarios rehearsed live and timed (API down, bad
  data, a wrong rule), 1 reused from real evidence already produced in
  step 8 (renamed column -- PR #13) rather than repeated identically,
  and 1 deliberately *not* physically performed (full disk -- genuinely
  destructive to rehearse safely on this machine), with the reasoning
  for that choice written down rather than silently skipped. Full
  detail, including exact timestamps, in `docs/postmortem.md`.

### A real finding from the game day, not fixed on the spot
Scenario 1 (API down) took **3 minutes 16 seconds** from flow start to
the Discord alert firing -- dominated by Prefect's own task-level retry
(`ingest_task(retries=3, retry_delay_seconds=60)`, 180s alone) stacked
on top of `pipeline/http_utils.py`'s lower-level HTTP retries. Both
layers are individually reasonable (ADR 0006), but their combination
means a real, sustained outage goes undetected for over three minutes
even with every retry mechanism "working as designed." Left as an open
question in the postmortem rather than changed reflexively -- a
deliberate decision about detection-speed vs. tolerance-for-blips, not
a bug.

### Verification
- Scenario 1 (API down): timestamps extracted directly from the real
  Prefect run log, not estimated -- `12:33:28.367` start to
  `12:36:44.586` alert logged.
- Scenario 2 (bad data): `1.36s` to Pandera refusal, confirmed nothing
  loaded.
- Scenario 3 (wrong rule): `4.43s` to `dbt build` reporting
  `PASS=17 ERROR=1 SKIP=25`; reverted immediately after, confirmed
  `git status` clean and a full `dbt build` passing again
  (`PASS=42/43`).

### Why this matters for the four promises
- **Observable**, proven rather than just built: the whole point of
  this step is confirming the mechanisms from steps 10-16 actually
  catch real, deliberately-introduced problems, with real numbers, not
  just existing in theory.
- **Reliable**: the full-disk scenario's honesty (reasoned through,
  not verified) is itself a reliability property worth keeping visible
  -- a postmortem that claims more rigor than it actually has would be
  the least reliable thing in this whole document.

### A question the individual exam could ask, answered here
**"Why does scenario 3 take 4 seconds and scenario 1 takes over 3
minutes, for what's conceptually the same kind of thing (a broken
pipeline)?"** They're not the same kind of thing. Scenario 3 is a local
`dbt build` -- one process, no network, no retries, fails the instant
the SQL runs. Scenario 1 goes through the actual production detection
path: HTTP-level retries, then Prefect's own task-level retries, each
layer adding real wall-clock delay by design (so a single flaky request
or a short blip doesn't trigger a false alarm). The individual exam's
version of this question is really asking: do you know which of your
checks run locally in seconds (lint, pytest, dbt build on a sample) and
which only surface in minutes through the full orchestrated path --
and that's exactly why CI's `data-quality` job (step 8) exists to catch
what it can before anything reaches orchestration at all.
