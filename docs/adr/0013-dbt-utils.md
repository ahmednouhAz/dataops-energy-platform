# ADR 0013 — Bonus: tried dbt-utils for real, reverted it for a real reason

## Decision
**Not adopted.** `dbt-labs/dbt_utils` was added (`packages.yml`) and
`dim_date.sql`'s hand-rolled date spine was replaced with
`dbt_utils.date_spine()`, specifically because `dim_date` was already
doing by hand exactly what that macro is built for -- the "actually use
it somewhere real" standard every other bonus item in this project held
itself to. Reverted after finding a real limitation, not a style
preference.

## What broke, and where it was found
`dbt build --target ci` (the exact command CI's `data-quality` job
runs) failed:
```
Compilation Error in model dim_date
upper bound must be positive
> in macro default__get_powers_of_two (dbt_utils/macros/sql/generate_series.sql)
> ... called by macro default__date_spine
```
Traced to the shape of `tests/fixtures/eco2mix_sample.csv` (step 7): all
10 rows are on the same single day, `2026-01-01` -- a deliberately tiny
fixture, by design, for a fast CI sample. `date_spine()`'s internal
`get_intervals_between` computes `datediff(min, max, 'day')`, which is
`0` when the span is a single day; its `generate_series` helper then
rejects a `0` upper bound outright. DuckDB's own native
`generate_series(min_date, max_date, interval '1 day')` -- what
`dim_date` used before, and reverted back to -- handles
`min_date == max_date` fine (returns exactly one row).

**This would not have been caught by testing against the dev
warehouse alone** (`dev.duckdb` spans 14 years, nowhere near a
single-day edge case) -- it only surfaced by running the exact command
CI runs, against the exact fixture CI uses, which is why `dbt build
--target ci` (not just `dbt build` on `dev`) is part of this project's
own verification habit for anything that touches a model used by both
targets.

## Why reverted instead of worked around
Padding the spine's bounds (e.g. `end_date + 1`) to dodge the zero-span
case would change `dim_date`'s actual reported date range for every
caller, not just the tiny-fixture edge case -- trading a real
correctness property (the dimension's bounds exactly match the real
data) for compatibility with a third-party macro's own internal
limitation. The hand-rolled version has no such limitation and needed
no such workaround. Per this ADR's own opening standard -- use the
package for something real, or don't add it -- once the one real use
case didn't hold up, keeping the dependency installed and unused would
have been worse than not adding it at all.

## Alternatives rejected
- Keep `dbt_utils` installed for *some* future use, unrelated to this
  specific finding: rejected -- an installed-but-unused dependency is
  exactly what this project's own standard (ADR 0011, ADR 0012) argues
  against elsewhere; there's nothing to point to as "the real usage"
  once `dim_date` reverted.
- Pad the bounds to avoid the zero-span case (see above): rejected --
  trades real correctness for compatibility with the macro's own
  internal limitation.
- Special-case the fixture (e.g. make `eco2mix_sample.csv` span 2 days
  instead of 1) to avoid tripping the macro: rejected -- the fixture's
  shape is a property of step 7's own design (a small, fast, known-
  reference CI sample), not something to change just to accommodate an
  unrelated bonus item's dependency.

## Verification
- `dbt build --select dim_date` and full `dbt build --full-refresh` on
  `dev`: both passed while using `dbt_utils.date_spine()` -- the bug
  only showed up against the `ci` target's tiny fixture, confirmed by
  reproducing it locally with the exact command
  (`dbt build --target ci`) before reverting.
- After reverting: `dbt build --target ci` passes again locally;
  `packages.yml`/`package-lock.yml`/`dbt_packages/` removed, the
  `dbt deps` steps added to `ci.yml`/`nightly.yml` removed (no longer
  needed), `.sqlfluffignore`'s `dim_date.sql` entry removed (the
  reverted model has no package-macro call to exclude for).
- `dbt build --full-refresh` (full project, `dev`): `PASS=42/43`,
  identical to before this bonus item was attempted.
