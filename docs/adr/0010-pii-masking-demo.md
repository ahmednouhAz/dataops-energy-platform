# ADR 0010 — A masking macro, demonstrated and tested, applied to nothing real

## Decision
- `macros/mask_pii.sql`: a dbt macro with two techniques --
  `mask_pii(column)` (full pseudonymization, SHA-256) and
  `mask_pii(column, visible_chars=N)` (partial redaction, keeps the last
  N characters visible, masks the rest).
- `models/governance/demo_pii_masking.sql`: a tiny view applying both
  variants to literal example values, with 2 dbt unit tests
  (`models/governance/governance.yml`) pinning the exact expected
  output for a known input -- proof the mechanism actually works, not
  just that it compiles.
- **Not applied to any real column.** `contracts/eco2mix_regional.yaml`
  and `contracts/weather_hourly.yaml` have said so since step 7
  (`contains_pii: false`, with a `pii_note` explaining why: every row is
  a region-level aggregate, never an individual or household).

## Why build this at all, if nothing needs it
CLAUDE.md section 5's governance checklist is explicit: "personal data
masked (our data has no personal data: document it explicitly in the
contracts, and show the masking mechanism anyway, e.g. a macro)." The
contracts already did the documenting (step 7); this step does the
showing. The alternative -- writing only a paragraph claiming "we'd use
hashing if we ever needed to" -- isn't verifiable and isn't the kind of
claim this project holds itself to anywhere else (every other ADR in
this repo backs a decision with something actually run, not just
described).

## Why a real (if tiny) model instead of only documentation
A macro that's never invoked by anything isn't provably correct --
Jinja macros can reference undefined variables, call functions a given
SQL dialect doesn't have, or simply have a typo, and none of that
surfaces until something actually compiles and runs them. Confirmed
this mattered in practice before committing to the final design: tested
DuckDB's `sha256()`/`repeat()`/`right()`/`greatest()` functions directly
first, then built the real demo model and ran its unit tests
(`dbt build --select demo_pii_masking`: `PASS=3`), rather than writing
the macro from memory and assuming it would work.

## Why a `governance/` folder, not a new mart
`demo_pii_masking` isn't part of the star schema and has no business
meaning -- putting it in `marts/` would misrepresent what the fact/
dimension layer actually is, and would need explaining away at the
defense ("why is there a PII-masking fact table with no PII?").
`+materialized: view` (not `table`) in `dbt_project.yml` keeps it from
adding to the physical warehouse at all beyond a query definition.

## Alternatives rejected
- A paragraph of documentation with no runnable code: rejected under
  "Why build this at all" above.
- Applying the macro to a real column that isn't actually PII, just to
  have "real" usage (e.g. masking `region_name`): rejected -- that would
  misrepresent a non-sensitive value as sensitive, the opposite problem,
  and would break every downstream join/display that currently uses the
  readable region name for no safety benefit.
- A Python-level masking function in `pipeline/schema.py` instead of a
  dbt macro: rejected because masking, if this project ever needed it
  for real, belongs at the point data becomes visible to a wider
  audience (the warehouse layer dashboards/exports read from), not
  baked into the raw ingestion step, which should keep raw data exactly
  as the source sent it (CLAUDE.md section 4's "raw = untouched"
  philosophy).

## Verification
- `dbt build --select demo_pii_masking`: `PASS=3` (1 view + 2 unit
  tests), both unit tests checking an exact, hand-computed expected
  value (`sha256('alice@example.com')` computed independently via
  DuckDB directly first, then pinned in the test).
- `dbt build` (full project): `PASS=42/43` (1 exposure is a no-op by
  design), no regressions.
- `dbt docs generate`: completes, catalog includes the new model and
  the step-14 exposure -- lineage stays documented end to end.
