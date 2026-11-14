-- One row per day spanning the eco2mix data we actually have, so the table
-- grows with the backfill (step 10) instead of being hard-coded to a fixed
-- date range.
--
-- Tried dbt_utils.date_spine() here for a step-18 bonus item; reverted
-- after finding a real limitation, not a style preference: it errors
-- ("upper bound must be positive") whenever the span is a single day --
-- exactly the shape of this project's own tests/fixtures/eco2mix_sample.csv
-- (every row on 2026-01-01), so CI's data-quality job broke on it. DuckDB's
-- own generate_series handles min_date == max_date fine (one row), which
-- is what this reverted-to version relies on. See ADR 0013.
with bounds as (
    select min(date_heure)::date as min_date, max(date_heure)::date as max_date
    from {{ ref('int_eco2mix_checked') }}
)

select
    d::date as date_day,
    extract(year from d) as year,
    extract(month from d) as month,
    extract(day from d) as day,
    extract(dow from d) as day_of_week,
    extract(dow from d) in (0, 6) as is_weekend
from bounds, generate_series(bounds.min_date, bounds.max_date, interval '1 day') as t(d)
