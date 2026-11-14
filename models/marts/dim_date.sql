-- One row per day spanning the eco2mix data we actually have, so the table
-- grows with the backfill (step 10) instead of being hard-coded to a fixed
-- date range. Uses dbt_utils.date_spine (step 18 bonus) instead of the
-- hand-rolled generate_series this model used before -- a tested,
-- community-maintained implementation of the exact same idea, not
-- something this project has to keep correct on its own. The start/end
-- dates are scalar subqueries (not a CTE reference) because date_spine
-- evaluates them in their own standalone statement at compile time
-- (see dbt_packages/dbt_utils/macros/sql/date_spine.sql).
with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="(select min(date_heure)::date from " ~ ref('int_eco2mix_checked') ~ ")",
        end_date="(select max(date_heure)::date from " ~ ref('int_eco2mix_checked') ~ ")"
    ) }}
)

select
    date_day::date as date_day,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(day from date_day) as day,
    extract(dow from date_day) as day_of_week,
    extract(dow from date_day) in (0, 6) as is_weekend
from spine
