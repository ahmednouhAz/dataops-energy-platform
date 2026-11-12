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
