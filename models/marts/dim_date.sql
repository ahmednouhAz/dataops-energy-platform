-- One row per day spanning the eco2mix data we actually have, so the table
-- grows with the backfill (step 10) instead of being hard-coded to a fixed
-- date range.
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
