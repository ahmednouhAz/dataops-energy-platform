# ADR 0008 — Dashboard: Metabase (not Evidence), self-hosted via Docker

## Decision
- **Metabase**, self-hosted, using the community-maintained
  `ghcr.io/motherduckdb/metabase-duckdb` image (official Metabase has no
  DuckDB driver at all; this image bundles the MotherDuck-maintained one
  on top of it).
- Reads `SERVING_DUCKDB_PATH` (the published copy), read-only, mounted
  into the container as `/data` -- never `prod.duckdb` directly, same
  write-audit-publish split every other reader of the warehouse already
  uses (ADR 0007).
- `scripts/setup_metabase.py`: a one-shot, idempotent script (run as the
  `metabase-setup` service in `docker-compose.yml`) that creates the
  admin user, adds the DuckDB connection, and builds the 3
  business-question cards + one dashboard, all through Metabase's own
  REST API -- no manual click-through needed on a clean machine.
- `models/exposures.yml`: declares the dashboard as a dbt exposure
  depending on exactly the 4 marts it reads
  (`fct_energy_production`, `fct_consumption_weather`, `dim_region`,
  `dim_energy_source`) -- satisfies "declared as a dbt exposure" and
  "reads only from marts" as one piece of documented lineage, checkable
  with `dbt docs generate`.

## CLAUDE.md's plan said "Metabase or Evidence, TO DECIDE" -- here's what deciding looked like
Evidence was the first choice actually attempted, on the reasonable
assumption (consistent with this whole project being DuckDB-first) that
it would have first-class local-DuckDB-file support. Scaffolding a real
Evidence project and reading its current self-host docs directly showed
that assumption was wrong:
- The scaffolding command (`npx degit evidence-dev/template`) produces a
  project built around **Evidence Studio**, a *hosted, login-gated*
  product -- `evidence login` requires a browser-based auth flow, and
  queries route through ClickHouse SQL by default. That alone breaks
  this project's "no paid account" / fully local constraint.
- The still-open-source **Evidence Core** does have a genuine,
  no-login self-host path (`evidence serve`, Docker image
  `evidencedev/serve`, confirmed to need "no Evidence Studio account or
  session required"). But its documented direct-connector list for
  self-hosting is Snowflake, Fabric, SQL Server, ClickHouse, BigQuery,
  Databricks, Postgres, Cube, Redshift, Athena, and MotherDuck -- **no
  local-DuckDB-file connector at all**. MotherDuck is DuckDB's own cloud
  service, not a `.duckdb` file on disk; everything else is a different
  database engine entirely.
- Loading the warehouse into one of those (e.g. standing up Postgres just
  to satisfy Evidence's connector list) would mean maintaining a second
  copy of the data in a second engine, for a dashboard-only purpose --
  a real cost for a tool that was supposed to be the simplest, lightest
  piece of the stack (CLAUDE.md: "the dashboard is the last and smallest
  piece").

**Metabase**, by contrast, has exactly one documented way to connect to a
local DuckDB file (a path string in a connection's `details`), and the
community driver, while not officially maintained by Metabase itself, is
actively released (most recent release about 4 weeks before this ADR was
written) and purpose-built by MotherDuck for exactly this case.

## Two real problems, found only by actually running it
1. **AccessDeniedException on Metabase's own app database.** The image
   runs as a non-root `metabase` user; mounting a *brand-new* named
   volume at a path the image doesn't already own (`/metabase-data`, a
   path invented for this compose file, not something the image's
   Dockerfile ever created) left that path owned by `root`, which the
   `metabase` user can't write to -- Metabase crashed on its own H2 app
   database before even reaching the setup wizard. Fixed by mounting the
   volume at `/home/metabase` instead -- the image's own working
   directory, already correctly owned for that user, so Docker's
   "populate a fresh volume from the image" behavior preserves the right
   ownership. Same root cause as ADR 0005's MinIO non-root-UID finding,
   different image.
2. **Host port 3000 was already Grafana's** (step 13). Metabase listens
   on 3000 inside its own container regardless; mapped to **3001** on
   the host instead of changing either service's internal port.

## Why script the API instead of documenting manual setup
Grafana (step 13) has a real provisioning-by-file convention; Metabase
does not. The alternative was "click through the setup wizard once, by
hand" -- works, but breaks the reproducibility bar every other service in
this stack already meets (`docker compose up` alone, verified, no manual
step). Metabase's `/api/setup` endpoint is literally what its own setup
wizard calls, found and confirmed by making the same calls directly with
`curl` before writing any script, not guessed from memory. Idempotency
(check-then-create on the database/cards/dashboard) means re-running
`docker compose up` -- or a teacher re-running it on exam day -- never
duplicates anything.

## A model change this step needed, upstream of the dashboard itself
Business question 3 ("which regions depend on imports... at peak
consumption") needs `ech_physiques_mw` (grid exchange) alongside
consumption, at the same region/hour grain -- not available in any
existing mart (`int_energy_production_unpivoted` deliberately excludes
it; it's an exchange, not a production source). Added it to
`int_consumption_hourly` and `fct_consumption_weather` as
`ech_physiques_mw_avg` (RTE's sign convention: positive = net export,
negative = net import) rather than inventing a new mart for one column
at the exact same grain an existing mart already has.

## Alternatives rejected
- Loading a copy of the warehouse into Postgres just to use Evidence's
  documented connector list: rejected under "Decision" above -- a second
  copy of the data in a second engine, maintained forever, just to use a
  tool that turned out not to fit this architecture after all.
- Metabase Cloud (removes the need to self-host the driver): can't
  install custom drivers at all, so the DuckDB connection wouldn't exist
  -- confirmed on Metabase's own data-sources page before even trying it.
- Documenting "click through the Metabase setup wizard once" instead of
  scripting it: rejected under "Why script the API" above.

## Verification
- `docker compose up -d metabase metabase-setup` on a wiped
  `metabase-data` volume (simulating a clean machine): Metabase reports
  `(healthy)`, `metabase-setup` exits with
  `Dashboard ready: http://metabase:3000/dashboard/2`.
- Re-ran `docker compose run --rm metabase-setup` a second time: same
  dashboard id returned, no duplicate database/cards/dashboard --
  idempotency proved directly, not assumed.
- All 3 cards executed via `/api/card/<id>/query`: `status: completed`,
  real rows back (e.g. Q3's peak-hour query returning each region's
  actual peak hour and MW figures from `serving.duckdb`).
- `dbt build`: PASS=39 with the new `ech_physiques_mw_avg` column (no
  `not_null` test on it -- a null average is a legitimate "no data that
  hour", not a quality defect, same reasoning as ADR 0004's nuclear-null
  finding).
