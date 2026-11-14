# ADR 0013 — Bonus: dbt-utils, used for real in `dim_date`

## Decision
`packages.yml` adds `dbt-labs/dbt_utils` (`>=1.3.0,<2.0.0`, resolved to
`1.4.1`, pinned in the committed `package-lock.yml`). `dim_date.sql`
now builds its date spine with `dbt_utils.date_spine()` instead of a
hand-rolled `generate_series` + `CROSS JOIN`.

## Why this, not a token "add the package and don't use it"
CLAUDE.md's bonus list names "dbt-utils / dbt-expectations + macros" --
the value is in actually using a macro somewhere real, not just having
the package installed. `dim_date` was the one model already doing by
hand exactly what `dbt_utils.date_spine()` is built for: a day-by-day
date spine bounded by the actual data range (step 5's own design,
"not hard-coded"). Swapping in the tested, community-maintained version
removes code this project would otherwise have to keep correct itself,
for a mechanism dbt-utils's own test suite already covers.

## A real mechanical detail, found by reading the macro's own source before using it
`date_spine()` evaluates its `start_date`/`end_date` arguments in their
**own standalone statement** at compile time (internally, via
`get_intervals_between` → a bare `select {{ datediff(...) }}` query) --
confirmed by reading `dbt_packages/dbt_utils/macros/sql/date_spine.sql`
directly rather than guessing from the macro's name. This means the
bounds can't be a CTE reference from the surrounding query (the old
`with bounds as (...)` pattern); they have to be self-contained SQL
expressions. Used scalar subqueries instead:
`"(select min(date_heure)::date from " ~ ref('int_eco2mix_checked') ~ ")"`.
Verified this actually produces the same bounds as the old
implementation (`5063` days, `2013-01-01` to `2026-11-11` -- matching
the dataset's actual range at the time of the test), not assumed from
the macro compiling without error.

## A second instance of an already-known sqlfluff limitation
Same root cause as `models/governance/demo_pii_masking.sql` (ADR 0011):
the lightweight jinja templater can't resolve a package macro
(`dbt_utils.date_spine`) any more than it could resolve a custom one.
Added `models/marts/dim_date.sql` to `.sqlfluffignore` next to the
existing `models/governance/` entry. Also found, while fixing this,
that `.sqlfluffignore` doesn't support an inline `# comment` after a
pattern on the same line the way `.gitignore` does -- it silently
treated the first attempt's `pattern  # comment` as part of the pattern
itself, so the exclusion didn't match at all until the comments were
moved to their own lines above the patterns.

## Alternatives rejected
- Installing dbt-utils without using it anywhere (just to tick the box
  that the package exists): rejected -- that proves nothing and adds a
  dependency for no benefit, the opposite of this session's own
  standard for every other bonus item.
- Keeping the hand-rolled `generate_series` version and only adding
  dbt-utils for some *other*, newly-invented model: rejected -- would
  mean maintaining two ways of doing the same thing (a date spine) in
  the same project for no reason, when one model was already doing
  exactly what the package macro replaces.

## Verification
- `dbt deps`: installs `dbt_utils` 1.4.1 cleanly.
- `dbt build --select dim_date`: `PASS=3` (1 table + 2 data tests).
- `dbt build --full-refresh` (full project): `PASS=42/43`, unchanged.
- Row count/bounds check (`query.py`): `5063` rows, `2013-01-01` to
  `2026-11-11` -- consistent with the dataset's real range.
- `sqlfluff lint models data_tests seeds`: clean, after fixing the
  `.sqlfluffignore` inline-comment mistake.
