-- The row-level quality rules. The first rule that matches wins (TP3 pattern).
-- No row is removed here either -- a rejected row keeps its place, with a
-- reason, and is routed to the eco2mix_rejected quarantine mart. Only rows
-- with reject_reason is null feed the star schema (int_energy_production_
-- unpivoted, int_consumption_hourly).
select
    *,
    case
        when code_insee_region is null then 'missing_region'
        when code_insee_region not in (select code_insee_region from {{ ref('regions') }})
            then 'unknown_region'
        when date_heure is null then 'invalid_timestamp'
        -- The real-time dataset publishes a region/timestamp row before its
        -- measurements are ready: the freshest few hours are legitimately
        -- null, not wrong (see ADR 0002 addendum) -- label it accordingly so
        -- the quarantine table doesn't claim consumption was negative when
        -- it was simply missing yet.
        when consommation_mw is null then 'missing_consumption'
        when consommation_mw < 0 then 'negative_consumption'
        -- A later load supersedes an earlier one for the same (region, timestamp):
        -- keep the row with the most recent _dlt_load_id, reject the rest.
        when row_number() over (
            partition by code_insee_region, date_heure
            order by _dlt_load_id desc
        ) > 1 then 'duplicate_region_datetime'
    end as reject_reason
from {{ ref('stg_eco2mix_regional') }}
