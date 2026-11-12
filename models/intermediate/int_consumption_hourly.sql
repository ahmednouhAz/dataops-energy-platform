-- eco2mix is 15-min (real-time) or 30-min (definitive) granularity; weather
-- is hourly. Aggregate consumption up to the hour so fct_consumption_weather
-- can join the two on the same grain. Clean rows only.
select
    code_insee_region,
    date_trunc('hour', date_heure) as observed_hour,
    avg(consommation_mw) as consommation_mw_avg
from {{ ref('int_eco2mix_checked') }}
where reject_reason is null
group by 1, 2
