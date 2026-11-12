# ADR 0002 — Source exploration: eCO2mix definitive vs real-time, Open-Meteo freshness

## Decision
- Use **`eco2mix-regional-cons-def`** (definitive) for the historical backfill, and
  **`eco2mix-regional-tr`** (real-time) for daily/incremental loads going forward.
  Both are confirmed to exist in the ODRÉ catalog (found via
  `search(dataset_id, "eco2mix")` on the `/catalog/datasets` endpoint).
- Treat the two datasets as **two separate dlt sources loading into the same raw
  table shape**, because their JSON schemas differ (see below) — staging must not
  assume one fixed Python type per column.
- `seeds/regions.csv` holds the 12 mainland France regions (confirmed via a
  `group_by` query on `code_insee_region, libelle_region`), each mapped to one
  representative city for the Open-Meteo weather call.

## What the exploration found

### eCO2mix: definitive vs real-time don't share one schema
Querying 5 sample records from each dataset (`scripts/explore_eco2mix.py`):

| Field | `cons-def` (definitive) | `-tr` (real-time) |
|---|---|---|
| `eolien` | **string** (`'193'`) | **int** (`207`) |
| `pompage`, `stockage_batterie`, `destockage_batterie` | `None` / int | **string** (`'0'`, `'-1'`) |
| `eolien_terrestre`, `eolien_offshore` | present (but `None` in our sample) | **absent** (30 fields vs 32) |
| junk trailing column | `column_30` | `column_68` |
| row count | 2,874,816 | 84,096 |
| date range | 2012-12-31 → 2026-08-31 | 2026-08-31 → 2026-11-12 (today, ~15 min granularity, effectively no lag) |

So the known `eolien`-is-a-string problem is **not consistent across sources**: it's
a string in the definitive dataset but an int in the real-time one. This is a
**Cohérence** (consistency) problem, not just a typing nuisance on one source: the
same physical quantity is encoded two different ways depending on which dataset
produced the row. Staging (`stg_eco2mix_regional`, step 4) must coerce every numeric
column with `try_cast`/`try_strptime` regardless of which source it came from,
never trust the JSON type.

The two datasets also hand off cleanly on dates: definitive's last row
(2026-08-31) lines up with real-time's first row (2026-08-31), so a cutover rule
("use definitive before date X, real-time from date X onward") is safe without an
overlap-dedup step at the boundary — though we still dedup defensively in
`int_eco2mix_checked` (step 5) in case that ever changes upstream.

### Open-Meteo: the "archive lags a few days" assumption in `CLAUDE.md` §7 was wrong
Requesting the last 10 days (`scripts/explore_weather.py`) returned **zero nulls**,
including the current hour of today. Requesting tomorrow returned an explicit `400`:
`"Parameter 'start_date' is out of allowed range from 1940-01-01 to 2026-11-12"` —
i.e. the allowed range's upper bound is exactly today, with no lag at the moment of
testing.

This doesn't mean the data for the last few days is final, though: Open-Meteo's own
documentation states that very recent days in the archive endpoint are filled from a
forecast model blend before being replaced by the final ERA5 reanalysis once it's
published (days to weeks later). So the risk here isn't **Complétude** (missing
values) but **Exactitude** (a value we load today for yesterday could be silently
revised if we re-fetch it later). We will not build a "wait N days before trusting
weather data" rule into the pipeline for now — it's not required by the brief and
would add complexity without a concrete failure we've observed — but this is written
down here so it isn't rediscovered the hard way during the Game Day.

**Action:** `CLAUDE.md` §7 should be corrected to drop the "archive lags a few days"
claim as stated, and note the forecast-blend revision risk instead.

### Not yet verified
- The bulk `/exports/{format}` endpoint (needed for an efficient backfill, instead of
  paginating `/records`) was not tested in this step — flagged for step 2
  (ingestion), not blocking step 1.

## Alternatives rejected
- Loading only the definitive dataset and waiting for it to be updated: it stops
  around 2026-08-31, more than two months of staleness — fails the "data arrives
  every day" requirement on its own.
- Loading only the real-time dataset for everything, including history: it only
  has ~84k rows (back to 2026-08-31), nowhere near the 1,000,000-row requirement.
