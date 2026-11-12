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
