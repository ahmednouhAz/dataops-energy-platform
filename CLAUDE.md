# CLAUDE.md — DataOps Energy Platform

> This file is read automatically by Claude Code at the start of every session.
> It is the single source of truth for **who I am, how to work with me, what the course taught, what the project requires, and where we are.**
> Keep it up to date: at the end of every step, update the "Current status" section at the bottom.

---

## 1. Who I am and how you must work with me

I am a student doing the DataOps course project **alone** (the brief assumes teams of 3–4). I missed most classes: I am an **absolute beginner** in Git, the terminal, Docker, SQL/dbt, DuckDB, CI/CD, orchestration and monitoring.

There is an **individual practical exam** where I work alone on this repo (fix an incident, add a source or a model, get it through CI), and a **live defense** where the jury breaks something and I must repair it and answer questions. **AI help is allowed, but I must be able to explain every line of the repo.** So your job is to be my **teacher and senior engineer**, not to code for me silently.

### Teaching rules (non-negotiable)

1. **Use the exact format of the course handouts (TP)** for every step. The teacher wants this format:
   - **Objectif** — what we are trying to achieve and *why it matters for the platform* (link it to one of the 4 promises: Automatic, Reliable, Reproducible, Observable).
   - **Les notions** — each new concept or tool explained in plain words *before* we use it: what it is, what problem it solves, what we would do without it, an everyday analogy if useful.
   - **À faire** — the files to create and the exact commands to type, in order. Give commands for my OS (see §2).
   - **Lisez chaque ligne** — after each code block, explain the important lines one by one (like the TPs do: "`all_varchar = true` loads every column as text, because…").
   - **Vérification** — exactly what I must see if it worked (output, numbers, files). I don't continue until I have seen it.
   - **Si ça ne marche pas** — a small table of the likely errors and their fix.
   - **Questions** — 2–4 questions like the TPs (Q1, Q2…) that check I understood. I answer them in `docs/learning_log.md`; you correct my answers.
2. **Small steps.** One brick at a time. Never create 15 files at once. Stop after each step and wait for me to paste the verification output.
3. **Explain before you write.** Before editing or creating files, say in 2–5 lines what you are going to do and why. Then do it. Then explain what you did.
4. **Prefer simple, readable code** over clever code. Same style as the TPs: short functions, a docstring on every function, comments that say *why*. English for code, comments, commit messages and identifiers.
5. **Never hide magic.** If a tool generates files or does something implicitly (dlt schemas, dbt compiled SQL, Docker networks…), show me where to look.
6. **When I make a mistake, explain the cause**, not just the fix. When *you* make a mistake, say so plainly and fix it.
7. **Quiz me** at the end of each brick with the kind of task the individual exam will have ("the API renamed a column, what breaks, where do you fix it?").
8. If I ask you to "just do it", you may go faster, but still leave a short explanation in `docs/learning_log.md`.
9. **Never commit secrets.** Never push directly to `main` (see §6). Ask before any destructive command (`rm -rf`, `git reset --hard`, `docker volume rm`, force push).

### Language
- Code, comments, commit messages: **English** (as in the TPs).
- Explanations to me: **English**, simple words. I'm francophone, so French terms from the course (Objectif, Vérification, quarantaine, porte de qualité…) are welcome.
- Final docs (README, ADRs, runbook, postmortem): **[FILL IN: French or English]**.

---

## 2. My setup

- **Main machine: my desktop PC at home** (powerful). OS: **Windows 11 Pro**. All the heavy work (Docker, full platform, backfill) happens here.
- **Laptop at university** (weak): only used through **GitHub Codespaces** in the browser. Both machines are kept in sync with GitHub (`git push` when I stop, `git pull` when I start).
- GitHub user: `ahmednouhAz`, repo: `dataops-energy-platform` (public).
- Editor: VS Code with the Claude Code extension (Claude Pro).
- Python: **3.12** in a virtual environment `.venv` at the repo root (TP style: `python -m venv .venv`, then `pip install -r requirements.txt`). The TPs required Python 3.10–3.13: **not 3.14**, dbt doesn't support it yet.
- On Windows: PowerShell is the TP shell. Activation: `.venv\Scripts\Activate.ps1`. Exit code: `echo $LASTEXITCODE` (not `echo $?`). If activation is blocked: `Set-ExecutionPolicy -Scope Process RemoteSigned`.

### Known history (what already happened)
- Step 0/1 done in Codespaces: repo created, PR #1 merged (devcontainer, `requirements.txt`, `.gitignore` additions, `docs/business_questions.md`, `docs/adr/0001-topic-and-architecture-level.md`).
- The `.devcontainer/devcontainer.json` **failed to build** in Codespaces twice (Codespaces fell back to an Alpine "recovery container" without our tools). The last change pinned `python:1-3.12-bookworm`; it may or may not have been pushed. **TODO later (before using Codespaces at uni):** fix the devcontainer and verify it builds (check the creation log for the real error). A known-good fallback is the default `mcr.microsoft.com/devcontainers/universal:2` image + a `postCreateCommand` that creates a Python 3.12 venv.
- Repo hooks on the recovery machine complained about `git-lfs`. We don't use Git LFS. If that message appears locally, ignore it or run `git lfs install` once.

---

## 3. Course materials

The original handouts (converted to Markdown) are in `course/` (gitignored: they are the teacher's material, not mine to publish):

| File | Content |
|---|---|
| `course/PROJET.md` | **The project brief. Read it when in doubt about a requirement.** |
| `course/TP1.md` | From a fragile script to a tested pipeline (pandas, quality rules, quarantine, pytest, Git) |
| `course/TP2.md` | Git branches and DVC (data versioning, remote, tags, going back to old data) |
| `course/TP3.md` | ELT with DuckDB and dbt (raw load, staging/intermediate/marts, tests, unit tests, lineage) |
| `course/TP4.md` | Quality gate: ODCS data contract, Pandera, 3-job GitHub Actions CI, nightly workflow |

Read the relevant TP **before** building the corresponding brick, and reuse its patterns, names and commands. When the project needs something the TPs didn't cover (dlt, Docker Compose, MinIO, Prefect, Grafana, Metabase/Evidence…), teach it from zero with the same format.

---

## 4. Course conventions to follow (summary of TP1–TP4)

These are the patterns the teacher expects to see again in the project, scaled up.

### TP1 — Pipeline thinking and data quality
- A script can **run without errors and still be wrong** (a "silent error"). Reliability comes from checks, not from the language.
- The **5 data quality dimensions** (use these words in docs and tests): **Complétude** (is something mandatory missing?), **Unicité** (is something counted twice?), **Validité** (do values respect the rules?), **Cohérence** (is the same thing written the same way?), **Exactitude** (does the value match the real world?).
- Three reactions to bad data:
  1. **The whole file is unusable** (missing column, empty file) → **stop** (`DataQualityError`), publish nothing, exit code 1.
  2. **A few bad rows** → **quarantine** them with a `reject_reason`, keep the good ones. A fixable problem (spelling, spaces) is **repaired**, not rejected.
  3. **Too many bad rows** (reject rate > 20 %) → **stop** too: the problem is the file, not the rows.
- Rules are applied in order and **the first matching rule wins** (one `reject_reason` per row).
- **Unit test (code test)** = my logic on a tiny hand-written table, run when the code changes (pytest, `tests/`). **Data check (data test)** = today's real data, run at every execution. Both are needed.
- Exit codes matter: `0` = success, `1` = stopped. The orchestrator and the CI read them.
- We version the **code**, not the files the code produces (`.gitignore`).

### TP2 — Git and DVC
- Every change on a **branch**, merged into `main` (in a team: via a pull request reviewed by someone).
- **Data doesn't go in Git.** DVC stores it in a remote (here: a folder or MinIO/S3) and Git keeps a small pointer file (`*.dvc`) with an **md5** fingerprint.
- `dvc add`, `dvc push`, `dvc pull`, `dvc checkout`, tags like `data-v1`. Going back in time = `git checkout <tag> -- data/x.dvc` + `dvc checkout`.
- Reproducibility test: someone else does `git clone` + `dvc pull` and gets **the same number**.
- In the project: DVC tracks **reference datasets and test samples** (brief requirement).

### TP3 — ELT with DuckDB + dbt
- **ELT, not ETL**: load the raw data **as-is** into the warehouse first, transform later **in SQL** inside the warehouse. Keeping the raw data means a wrong rule can be fixed and replayed.
- **Raw load convention** (`load_raw.py` in TP3): schema `raw`, **all columns as text** (`all_varchar = true`), plus loader metadata columns starting with `_`: `_row_number`, `_source_file`, `_loaded_at`. (In the project dlt does the load and adds its own `_dlt_load_id`, `_dlt_id`; we keep the same philosophy: raw = untouched, metadata columns start with `_`.)
- `query.py "select …"`: a tiny tool to query the warehouse in read-only mode. Keep it in the project.
- dbt project **at the repo root**: `dbt_project.yml`, `profiles.yml` (no secrets in it), `models/`, `data_tests/` (dbt tests are kept apart from pytest's `tests/`). Run dbt **from the repo root**.
- Install **`dbt-duckdb`** (dbt Core 1.x), **never the bare `dbt` package** (that's dbt v2/Fusion, not what the course uses).
- Layers and materializations:
  - `models/sources.yml` declares the raw tables (+ freshness in the project).
  - `staging/stg_*.sql`: **one per source table**; gives each column its real type with `try_cast` / `try_strptime` (NULL instead of crash), repairs what can be repaired (trim, case), **removes no row**. Materialized as **view**.
  - `intermediate/int_*_checked.sql`: applies the business rules with a `case when … then '<reason>' end as reject_reason` (first match wins); dedup with `row_number() over (partition by <key> order by <load order>) > 1`. **View**.
  - `marts/`: what users read. A clean table, a **rejected/quarantine table**, and report tables. **Table** (incremental for the big fact in the project).
- Each model is one `select`; dependencies via `{{ source() }}` and `{{ ref() }}`, which is how dbt knows the order and draws the **lineage**.
- Tests:
  - **Generic** in YAML (`unique`, `not_null`, `accepted_values` with the `arguments: values:` syntax, `relationships`).
  - **Singular** in `data_tests/assert_*.sql`: a query that returns the bad rows. **A test passes when it returns no rows.** E.g. `assert_reject_rate_below_20_percent.sql` with `having … > 0.20 * count(*)`.
  - **dbt unit tests** in a `.yml` next to the model (`unit_tests:` with `given` / `expect`), named `test_<behaviour>`. Read them as "Given… When… Then…".
- **`dbt build`** builds and tests in DAG order and **SKIPs everything downstream of a failure** ("arrêter la chaîne"): the previous report stays published.
- `dbt docs generate` + `dbt docs serve --port 8081` → lineage graph.
- Expected output style in verifications: `Done. PASS=14 WARN=0 ERROR=0 SKIP=0`.

### TP4 — Quality gate
- A CI can turn red **without anyone touching the code** (data changed, library changed, file missing). Two threats: **the data changes** (supplier renames a column) and **the code changes** (a colleague breaks a rule).
- **Data contract** per source, `contracts/<source>.yaml`, **ODCS v3.2.0** format (`kind: DataContract`, `apiVersion: v3.2.0`, `servers:`, `schema:` → `properties:` with `physicalType`, `logicalType`, `required`; `team:` = owner). It describes the **shape** of the data (columns, types, required), **not the business rules** (those stay in dbt). Commands: `datacontract lint contracts/x.yaml`, `datacontract test --server ci contracts/x.yaml`. The old DCS format (`models`/`fields`) is deprecated: don't use it.
- **Pandera** at the entrance of the load (`pipeline/schema.py`): `strict=True` (extra/missing column → refused), `coerce=True`, whole-column plausibility checks (e.g. "≥ 80 % of the values plausible"), `validate(df, lazy=True)` to collect all errors; on failure print `REFUSED: …` with `failure_cases`, `sys.exit(1)`, **load nothing**. Pandera judges the whole file; dbt judges row by row.
- **CI sample** in `tests/fixtures/` (small, in Git) with a **known reference number** → **regression test** (`report_md.py <expected>` exits 1 with `REGRESSION: expected …, got …`).
- **`.github/workflows/ci.yml`**: `on: pull_request` + `push` on `main`; **three chained jobs** with `needs:`, from fastest to slowest: `lint` (ruff) → `python-tests` (pytest) → `data-quality` (contract on sample → Pandera + load sample → `dbt build` → report to `$GITHUB_STEP_SUMMARY` → `upload-artifact` of `target/run_results.json` with `if: always()`). `actions/setup-python@v5` with `python-version: "3.12"` and `cache: pip`.
- **`.github/workflows/nightly.yml`**: `schedule: cron "0 5 * * *"` (UTC) + `workflow_dispatch`; rebuilds everything, `dbt docs generate`, uploads the docs as an artifact.
- **A red PR is never merged.** Demonstrated with a "supplier PR" (renamed column → contract red) and a "colleague PR" (broken rule → unit test red, `data-quality` not even started).
- Gotcha from TP4: `datacontract-cli` requires **DuckDB 1.x**. If the DuckDB version changes, the old `.duckdb` file can't be read ("version number 69…") → delete it and rebuild (it's a rebuildable file, that's why it's gitignored).

---

## 5. The project (summary of `course/PROJET.md`)

Build a **complete data platform**: automatic ingestion of real sources, a warehouse, tested transformations, CI/CD, orchestration, monitoring and governance. "We are the data platform team of an organisation that wants to decide from reliable data. Today its numbers come from hand-downloaded files and scripts nobody dares touch."

**Four promises:** **Automatic** (data arrives every day without a human) · **Reliable** (wrong data is blocked before reaching a dashboard) · **Reproducible** (a newcomer clones the repo and runs everything with one command) · **Observable** (we always know whether data is fresh, complete and correct).

> "This is not a dashboard project. The dashboard is the last and smallest piece. What is graded is everything that makes it trustworthy."

### Hard constraints
- ≥ 2 sources, ≥ 1 API queried automatically, at least one changing **every day**.
- **≥ 1,000,000 rows** in the warehouse after the history backfill.
- ≥ 3 business questions (written in `docs/business_questions.md`), answered by the dashboard.
- No paid account. Everything runs with Docker on my computer, or in GitHub Codespaces.

### Our choices (see `docs/adr/0001-topic-and-architecture-level.md`)
- **Topic 2 — Energy**: eCO2mix regional data (RTE, via the ODRÉ Opendatasoft API) + Open-Meteo weather.
- **Architecture level 1** (mandatory): ELT warehouse, dlt → DuckDB → dbt. Built so we can move to level 2 (Parquet/Iceberg on MinIO) later without rewriting.
- **Orchestrator: Prefect 3** (lighter than Airflow for a solo project).
- **Dashboard: [TO DECIDE in an ADR: Metabase or Evidence]**.

### Concepts I must be able to explain at the defense
ELT · medallion architecture (bronze = `raw`, silver = `staging` + `intermediate`, gold = `marts`) · lakehouse · separation of storage and compute (MinIO stores, DuckDB computes) · open table format (Iceberg) · star schema (`fct_` facts + `dim_` dimensions: who, where, when) · data contract · data mesh (a **named owner** per source and per mart) · batch vs streaming.

### Requirements checklist — MANDATORY (without these the platform is not validated)

Copy this checklist into `docs/PROGRESS.md` and tick items as they are done.

**Version control**
- [ ] Git, one branch per change, every change through a pull request (solo: self-review comment + green CI; confirm the rule with the teacher)
- [ ] DVC for reference datasets and test samples

**Transformation (dbt on DuckDB)**
- [ ] `sources.yml` for each source with a **freshness** check (`dbt source freshness`)
- [ ] one `stg_` model per source table, `int_` models
- [ ] star-schema marts: ≥ 1 `fct_` and ≥ 2 `dim_`; **≥ 8 models in total**
- [ ] `unique` + `not_null` on every key, `relationships` between facts and dimensions, `accepted_values` on closed-list columns
- [ ] ≥ 2 singular tests and ≥ 2 unit tests
- [ ] ≥ 1 **incremental** model for the big fact table
- [ ] a description for every mart and every mart column; `dbt docs generate`
- [ ] one warehouse file per environment (`dev.duckdb`, `prod.duckdb`) chosen by the dbt target; CI builds on a sample in seconds

**Quality**
- [ ] a data contract per source (ODCS), with **owner** and **retention period**
- [ ] dbt generic + singular tests, ≥ 2 unit tests, a **quarantine table**

**Continuous integration**
- [ ] GitHub Actions on every PR: lint, pytest, contract, `dbt build` on a sample
- [ ] a red PR **cannot** be merged (branch protection on `main` with required status checks)

**Environment**
- [ ] `docker compose up` starts the whole platform
- [ ] MinIO object storage
- [ ] `.env.example` committed, `.env` gitignored, **no secret in the repo**

**Orchestration (Prefect)**
- [ ] one scheduled run per day: ingestion → `dbt build` → dashboard refresh
- [ ] automatic retries with delay, an alert on failure, readable logs in the UI
- [ ] **backfill**: replay history day by day with a date parameter, **without duplicates**

**Ingestion (dlt)**
- [ ] incremental and **idempotent** (running twice gives the same result)
- [ ] history loaded by backfill

**Continuous delivery**
- [ ] Docker images published to **GHCR** on each tag
- [ ] **dev and prod** environments
- [ ] documented **rollback**

**Observability**
- [ ] duration, rows, rejects and freshness in **Grafana** (via Prometheus)
- [ ] an alert on **Discord or Slack**
- [ ] a written **freshness objective** (SLO)

**Governance & security**
- [ ] **gitleaks** in CI
- [ ] personal data masked (our data has no personal data: document it explicitly in the contracts, and show the masking mechanism anyway, e.g. a macro)
- [ ] owner + retention in each contract; documented lineage

**Consumption**
- [ ] a dashboard (Metabase or Evidence) answering the 3 business questions, **reading only from the marts**

**Final deliverables**
- [ ] repo with `main` in defense state and a tag `v1.x`
- [ ] README that lets a stranger run everything
- [ ] architecture diagram
- [ ] ADRs: one page per important choice (what, why, rejected alternatives) in `docs/adr/`
- [ ] runbook: what to do when the alert fires (`docs/runbook.md`)
- [ ] postmortem of the game day (`docs/postmortem.md`)

### ADVANCED (bonus) — do the cheap, high-value ones once the core is done
Easy wins first: pre-commit hooks · conventional commit messages · protected `main` · SQLFluff · dbt-utils / dbt-expectations + macros · model contracts (`contract: enforced`) on marts · dashboard declared as a dbt **exposure** · Pandera at ingestion + published quality report · devcontainer (Codespaces) · CI under 5 minutes · snapshot of a changing dimension · slim CI (`--select state:modified+`) · day partitions + schema evolution · write-audit-publish + manual approval before prod · incident dashboard + SLO tracking over time · OpenLineage + Marquez · level 2 lakehouse (Parquet → Iceberg on MinIO, time travel) · LLM test assistant validated by CI · "data health" page for users.

### Defense and evaluation
- **Defense (20 min):** 5 min architecture and choices; 10 min live demo (an ingestion, the quality tests, **a PR blocked by CI**, the orchestration, the monitoring, then **the jury breaks something and I repair it**); 5 min questions.
- **Game day:** graded on time to detect, time to repair, and the quality of the postmortem.
- **Individual exam:** alone on the repo: fix an incident, add a source or a model, get it through CI.
- Graded areas: quality & tests (no wrong number published) · CI/CD · ingestion & orchestration · reproducibility (`git clone` + `docker compose up`) · observability & governance · advanced level · documentation · game day · defense · individual exam. **The Git history shows who wrote, reviewed and merged what.**

---

## 6. Git workflow (every single change)

```
git switch main
git pull
git switch -c <type>/<short-name>        # feat/ fix/ chore/ docs/ test/ ci/ refactor/
… edit files, run checks locally (ruff, pytest, dbt build) …
git add <files>
git commit -m "<type>: <imperative summary>"   # e.g. "feat: ingest eCO2mix regional data with dlt"
git push -u origin <branch>
```
Then on GitHub: open the PR (with a short description: what, why, how I tested) → wait for the CI to be green → write a self-review comment → **Merge** → delete the branch. Never `git push` to `main` directly. Never merge a red PR. Commit often, in small commits: my history is graded.

---

## 7. Technical design (energy topic)

### Sources (verified on 2026-11-12)
1. **eCO2mix regional** — Opendatasoft API `https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-regional-cons-def/records`. No key. ~2.87 M rows (since 2013, every 30 min, 12 regions of mainland France). Fields seen: `code_insee_region`, `libelle_region`, `nature`, `date`, `heure`, `date_heure` (UTC ISO), `consommation`, `thermique`, `nucleaire`, `eolien` (**arrives as a string!** → a typing problem for staging), `solaire`, `hydraulique`, `pompage`, `bioenergies`, `ech_physiques`, `stockage_batterie`, `destockage_batterie`, `eolien_terrestre`, `eolien_offshore`, `tco_*`, `tch_*` (coverage and load-factor ratios), `column_30` (junk column, always null). Values in MW.
   - `cons-def` = **consolidated/definitive** data (history, for the backfill). For the **daily** feed, find the **real-time** regional dataset in the ODRÉ catalog (likely `eco2mix-regional-tr`; **verify** its id and fields) and explain the difference definitive vs real-time in an ADR.
   - **API limits to design around (verify in the Opendatasoft docs):** the `/records` endpoint is paginated (max 100 per page, offset + limit capped around 10,000). For the bulk backfill use the **`/exports/{format}`** endpoint (CSV/JSON/Parquet, no pagination cap) with a `where` filter on `date_heure` (e.g. one month or one day at a time).
2. **Open-Meteo** — archive API `https://archive-api.open-meteo.com/v1/archive` (no key, free for non-commercial use; daily call limit to respect). Hourly `temperature_2m` (+ e.g. `wind_speed_10m`, `shortwave_radiation`, `cloud_cover`). One representative point per region (a seed file `seeds/regions.csv`: `code_insee_region`, `region_name`, `city`, `latitude`, `longitude`). The archive **lags a few days** behind today: for the last days use the forecast API with `past_days`, or set the freshness SLO accordingly (document this in an ADR).

### Grain and model sketch (to refine with me, step by step)
- `raw.eco2mix_regional`, `raw.weather_hourly` — loaded by dlt, untouched.
- `stg_eco2mix_regional` (types, `eolien` cast, junk column dropped, timestamps in UTC), `stg_weather_hourly`.
- `int_eco2mix_checked` (rules → `reject_reason`: missing region, invalid timestamp, negative consumption, duplicate region × timestamp, unknown region…), `int_energy_production_unpivoted` (one row per region × timestamp × energy source), `int_weather_by_region_hour`.
- Marts (star): `fct_energy_production` (region × half-hour × source, MW — **incremental**, the big table: ~2.9 M × ~8 sources ≈ 20 M rows), `fct_consumption_weather` (region × hour: consumption + temperature), `dim_region`, `dim_energy_source` (with `is_renewable` — `accepted_values` test), `dim_date`, `eco2mix_rejected` (quarantine), + small report marts for the 3 business questions.
- dlt loading: `write_disposition="merge"` with `primary_key=("code_insee_region", "date_heure")` (and region + time for weather) → **idempotent**: running twice, or re-running a backfill day, never creates duplicates. Date parameters `start_date` / `end_date` for backfill.

### Important technical constraints to teach me
- **DuckDB concurrency:** one process can open a `.duckdb` file in read-write mode, *or* several processes in read-only mode, not both. So the dashboard and Grafana must not hold the prod file open while dbt writes. Design for this (e.g. dbt builds `prod.duckdb`, then a "publish" step copies it to a read-only serving file that the dashboard reads; this is also the idea behind write-audit-publish).
- **Environments:** dbt targets `dev` (`dev.duckdb`), `prod` (`prod.duckdb`) and `ci` (the sample), selected with `--target`. Paths come from environment variables (`.env`), never hard-coded secrets.
- **Docker Compose services** (added progressively): MinIO, Prefect server, the pipeline worker (our image), Prometheus (+ Pushgateway for batch metrics), Grafana, Metabase/Evidence. Pin image versions.
- **Metrics per run** (written by the flow): duration, rows loaded per source, rows rejected, reject rate, max `date_heure` (freshness), success/failure, pushed to Prometheus, charted in Grafana, with an alert rule → Discord webhook (URL in `.env`).

### Target repo layout (grow it progressively, TP style)
```
dataops-energy-platform/
├── CLAUDE.md                 # this file
├── README.md                 # how a stranger runs everything
├── requirements.txt          # pinned ranges
├── .env.example              # every variable, no real secret
├── .gitignore
├── docker-compose.yml
├── Dockerfile                # pipeline image (published to GHCR)
├── .pre-commit-config.yaml
├── .devcontainer/
├── .github/workflows/        # ci.yml, nightly.yml, release.yml
├── pipeline/                 # Python: ingestion (dlt sources), schema.py (Pandera), metrics
├── flows/                    # Prefect flows: daily run, backfill
├── query.py                  # TP3 tool: query the warehouse
├── report_md.py              # TP4 tool: report + reference number (regression test)
├── dbt_project.yml           # dbt at the repo root, as in TP3
├── profiles.yml              # targets dev / prod / ci, paths from env vars
├── models/
│   ├── sources.yml
│   ├── staging/
│   ├── intermediate/
│   └── marts/
├── data_tests/               # dbt singular tests
├── seeds/                    # regions.csv, energy_sources.csv
├── macros/
├── contracts/                # one ODCS YAML per source
├── tests/                    # pytest + tests/fixtures/ (CI samples, known reference numbers)
├── monitoring/               # prometheus.yml, grafana provisioning + dashboards + alert rules
├── dashboard/                # Metabase or Evidence
├── data/                     # local data (gitignored or DVC-tracked)
├── course/                   # teacher's handouts (gitignored)
└── docs/
    ├── business_questions.md
    ├── PROGRESS.md           # the requirements checklist, ticked as we go
    ├── learning_log.md       # my answers to the questions + what I learned per step
    ├── architecture.md       # + diagram
    ├── adr/                  # 0001-…, 0002-…
    ├── runbook.md
    └── postmortem.md
```

---

## 8. Roadmap (one brick at a time, in this order)

Each step ends with: the verification passed → answers to the questions in `docs/learning_log.md` → commit(s) → PR → green CI (once it exists) → merge → update §9 and `docs/PROGRESS.md`.

| # | Brick | Main deliverables | TP to reuse |
|---|---|---|---|
| 0 | **Local setup** on the desktop | Python 3.12, Git, VS Code, Docker Desktop checked; repo cloned; `.venv` + `pip install`; `course/` in place and gitignored; `docs/PROGRESS.md`, `docs/learning_log.md` created | TP1 step 0 |
| 1 | **Explore the sources** | small script/notebook to call both APIs, look at fields, nulls, types, volumes; `seeds/regions.csv`; ADR 0002 (sources: definitive vs real-time, API limits, freshness) | TP1 step 1 (find the data problems, name the quality dimension) |
| 2 | **Ingestion with dlt** | dlt sources for eCO2mix and Open-Meteo → `raw` schema in `dev.duckdb`; date parameters; merge/primary key → idempotent (prove it: run twice, same count); `query.py` | TP3 step 1 (raw as-is) |
| 3 | **Pandera at the entrance** | `pipeline/schema.py` per source; refuse an unusable batch, load nothing, exit 1 | TP4 step 3 |
| 4 | **dbt project + staging** | `dbt_project.yml`, `profiles.yml` (dev/prod/ci), `sources.yml` with freshness, `stg_` models | TP3 steps 2–3 |
| 5 | **Rules, quarantine, marts in star** | `int_*_checked` with `reject_reason`, quarantine mart, `fct_`/`dim_`, incremental fact, seeds; ≥ 8 models | TP3 step 4 |
| 6 | **dbt tests + docs** | generic tests on every key, relationships, accepted_values; ≥ 2 singular (incl. reject rate); ≥ 2 unit tests; descriptions; `dbt docs` | TP3 steps 5–7 |
| 7 | **Pytest + data contracts** | pytest on the Python code; `contracts/*.yaml` (ODCS, owner, retention, PII = none); CI sample in `tests/fixtures/` + reference numbers; `report_md.py` | TP1 step 4, TP4 steps 2 & 4 |
| 8 | **CI quality gate** | `ci.yml` (lint → python-tests → data-quality, + gitleaks), `nightly.yml`; branch protection on `main`; demo a red "supplier PR" and a red "colleague PR" (screenshots/links in docs) | TP4 steps 5–8 |
| 9 | **DVC** | reference datasets / samples under DVC, remote on MinIO (or a local folder first) | TP2 |
| 10 | **Backfill** | load history day by day / month by month to > 1 M rows; prove no duplicates (count before/after a re-run) | — |
| 11 | **Docker Compose** | `Dockerfile` for the pipeline, `docker-compose.yml` (MinIO, Prefect, worker…), `.env.example`; `git clone` + `docker compose up` works on a clean machine | — |
| 12 | **Orchestration (Prefect)** | daily flow (ingest → dbt build → publish → refresh), retries with delay, failure alert to Discord, backfill flow with a date parameter, logs in the UI | — |
| 13 | **Observability** | metrics → Prometheus (Pushgateway) → Grafana dashboard (duration, rows, rejects, freshness), alert rule → Discord, written freshness SLO | — |
| 14 | **Dashboard** | Metabase or Evidence answering the 3 questions, **marts only**, declared as a dbt exposure | — |
| 15 | **CD, dev/prod, rollback** | `release.yml`: build & push image to GHCR on tag `v*`; dev vs prod targets; rollback procedure documented and tested | — |
| 16 | **Governance** | PII statement + masking macro, owners & retention in contracts, lineage documented (dbt docs), gitleaks green | — |
| 17 | **Docs & game day** | README, architecture diagram, ADRs, runbook; rehearse game day (break things on purpose: API down, renamed column, bad data, full disk, wrong rule), time detection and repair, write the postmortem | — |
| 18 | **Bonus** | pick from the advanced list, cheapest first | — |

---

## 9. Current status (UPDATE AT THE END OF EVERY SESSION)

- **Date of last update:** 2026-11-12
- **Current step:** 0 — local setup on the desktop PC — **done**. Next: step 1, explore the sources.
- **Done:** GitHub repo `ahmednouhAz/dataops-energy-platform`; PR #1 merged (skeleton, `requirements.txt`, `docs/business_questions.md`, ADR 0001); both APIs answered correctly with curl. PR #2 merged (step 0: Python 3.12 installed alongside 3.14, `.venv` created and `requirements.txt` installed, Docker Desktop confirmed running, this folder turned into the real clone of the repo, `.gitignore` fixed to actually exclude `course/` and `.claude/`, `docs/PROGRESS.md` and `docs/learning_log.md` created).
- **Open issues:** devcontainer doesn't build in Codespaces (see §2) → fix before using the laptop at uni.
- **Next class session:** [FILL IN]
- **Project deadline / defense date:** [FILL IN]
- **Teacher's answer about working solo (PR reviews, roles):** [FILL IN]
