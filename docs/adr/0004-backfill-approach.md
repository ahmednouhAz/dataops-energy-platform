# ADR 0004 — Backfill via the bulk /exports endpoint, chunked by year

## Decision
- `pipeline/sources/eco2mix.py::fetch_definitive_backfill_rows` uses the
  Opendatasoft **`/exports/csv`** endpoint for the definitive dataset, not
  the paginated `/records` endpoint daily ingestion uses.
- `pipeline/backfill.py` chunks the backfill **one calendar year at a
  time**, for both eco2mix and weather, each chunk going through the same
  Pandera validation as ordinary ingestion before it's loaded.
- Idempotency comes from an explicit **delete-then-append** per chunk
  (`_delete_existing_chunk`), not dlt's `write_disposition="merge"` -- see
  "A second problem, found only after the first full run" below. Day-to-day
  ingestion (`pipeline/ingest.py`) keeps using `merge`; its batches are too
  small for the problem that forced this change here.
- Default range: 2013-01-01 to the cutover date (2026-08-31); the real-time
  dataset covers everything after that already, through normal daily runs.

## Final verified state (after the corrective full reload below)
- `raw.eco2mix_regional`: 2,877,672 rows, 2,877,336 distinct
  (`code_insee_region`, `date_heure`) keys -- the 336-row gap is exactly 14
  years x 24 rows, explained below (DST), not a bug.
- `fct_energy_production`: 16,560,648 rows after `dbt build --full-refresh`,
  `PASS=39 WARN=0 ERROR=0 SKIP=0`.
- Idempotency proven directly: re-ran the 2015 chunk a second time after
  the reload -- `raw.eco2mix_regional` row count for 2015 (210,240) and the
  global total/distinct-key counts (2,877,672 / 2,877,336) were identical
  before and after.

## Why /exports instead of /records
`/records` caps at 100 rows/page (step 2). A full history of ~2.87M rows
would need roughly 29,000 sequential requests -- impractical and almost
certainly rate-limited. `/exports/csv` has no such cap: one request for a
full year (~210,000 rows) took **35 seconds** in testing, versus an
estimated many hours of paginated `/records` calls for the same volume.

## Why chunk by year instead of one request for the whole range
Tested: one year is ~35s, ~39MB. The full ~14-year range would be one very
large request (several hundred MB, several minutes) with no visibility
into progress and no partial credit if it fails two-thirds of the way
through. Year chunks: resumable, visible progress, and each chunk's
validation failure doesn't lose chunks that already succeeded. Each year's
rows never overlap another year's, which is also what makes the
delete-then-append idempotency scheme below safe: a chunk's delete can
never touch another chunk's rows.

## A real problem found while running this, not anticipated in advance
The very first full backfill attempt died with
`ConnectionError: ... forcibly closed by the remote host` on an Open-Meteo
weather call, after the eco2mix half of that year's chunk had already
loaded successfully. Added `pipeline/http_utils.py::get_with_retries` (3
attempts, a few seconds apart) and wired it into every HTTP call in both
sources. This is not a substitute for Prefect's own retry/alerting (step
12) -- it's the minimum needed for a multi-hour, many-request backfill to
actually finish without a human babysitting every call.

## A second problem, found only after the first full run: `merge` gets slower as the table grows
The first complete attempt used `write_disposition="merge"` (same as
`pipeline/ingest.py`), on the assumption that if it's safe for daily
ingestion it's safe here too. It wasn't, at this volume: each year chunk
took noticeably longer than the last -- 1m42s for chunk 1, 8m27s by chunk
10 -- because `merge` re-scans the *entire* destination table on every
load to find matching keys, so the cost grows with the table, not with the
chunk. After ~50 minutes with only 10/14 years loaded (and an estimated 2+
hours still to go), the run was killed rather than let it keep slowing down.

Fixed by replacing `merge` with an explicit delete-then-append
(`_delete_existing_chunk` + `write_disposition="append"`): delete any rows
already in `[chunk_start, chunk_end)` by range (cheap, no table scan). then
append the freshly-fetched rows. Re-running a chunk replaces it instead of
duplicating it -- the same idempotency guarantee `merge` gives, but in
roughly constant time per chunk. Verified: one year chunk dropped from
8m27s (merge, late in the run) to 93.6s (delete-then-append).

## A third problem, found by comparing old vs. new chunks: `merge` had been silently hiding a duplicate
Re-running the 2015 chunk a second time (to prove idempotency) showed the
eco2mix row count change by +24 rows on the *first* re-run under the new
approach -- which should be impossible for an idempotent operation. Traced
to France's DST spring-forward transition (last Sunday of March): the
source API emits two rows for the same `(code_insee_region, date_heure)`
per region that day (`heure` '02:00' and '03:00' both mapping to the same
UTC instant) -- a genuine upstream artifact, not a pipeline bug (see the
`int_eco2mix_checked.sql` comment for how it's quarantined downstream).
The old `merge` write disposition had been **silently deduplicating this
at raw-load time** for every year it was used on (2013-2022), via its own
key-matching logic -- hiding the artifact from `int_eco2mix_checked`'s
dedup rule entirely for those years, while 2023+ (loaded with
delete-then-append, which preserves raw rows exactly as fetched) showed it
transparently in the `eco2mix_rejected` quarantine table. That
inconsistency -- the same real-world artifact handled two different ways
depending only on which year it happened to fall in -- contradicts the
"raw = untouched" philosophy (§4 of CLAUDE.md), so **all 14 years were
reloaded** with the corrected delete-then-append approach once it was
fixed, not just the years added afterward. Confirmed uniform afterward:
every year from 2013 to 2026 shows exactly 24 `duplicate_region_datetime`
rows (12 regions x 2 duplicate rows), 336 total, matching the raw
total-vs-distinct-keys gap exactly.

## CSV export quirks handled
- Delimiter is `;`, not `,` (Opendatasoft's export default for this
  portal) -- confirmed by inspecting the raw response before writing any
  parsing code, not assumed from the `/records` JSON shape.
- A missing value shows up as **two different placeholders** in the CSV
  export: an empty string, and (found in real 2013 `eolien` data -- a
  region where wind wasn't yet consistently metered) a literal `-`. Both
  are `null` in the `/records` JSON. `_normalize_backfill_row` maps both to
  `None` so nothing downstream (Pandera, dlt, dbt) needs to know which
  endpoint, or which placeholder, a row came from. Found because Pandera
  correctly refused the first 2013 chunk (`eolien` compared as `str` vs.
  `int`) rather than silently loading it -- the validation did its job.

## A related finding while reconciling the rebuilt fact table: not every "null" is a quality problem
After `dbt build --full-refresh` on the full reload, `fct_energy_production`
failed its `not_null` test on `production_mw` with 701,286 nulls.
Diagnosed per-region: concentrated in exactly 5 of the 12 regions
(Ile-de-France, Bretagne, Pays de la Loire, Bourgogne-Franche-Comte, PACA),
which have **zero nuclear capacity** and report null `nucleaire` for their
entire history -- not a tracking gap, just "not applicable" for that
region/source combination. Fixed in `int_energy_production_unpivoted.sql`
by filtering `where production_mw is not null` after the unpivot, rather
than quarantining these rows or forcing a `0` that would misrepresent "no
plant of this type" as "plant exists, produced zero."

## Alternatives rejected
- Backfilling only a few months "to clear 1M rows technically": would
  satisfy the letter of the requirement while contradicting the project's
  own stated interest in multi-year trends (`docs/business_questions.md`
  asks "how does it evolve month by month?" -- that question needs years of
  data, not weeks).
- Loading the CSV straight into DuckDB with `read_csv`, bypassing dlt:
  faster, but breaks the project's established rule that **dlt owns the
  raw load** (step 2) -- every raw row would stop getting `_dlt_load_id`/
  `_dlt_id`, and idempotency would depend on a hand-rolled upsert instead of
  dlt's `merge` disposition, which is already tested.
