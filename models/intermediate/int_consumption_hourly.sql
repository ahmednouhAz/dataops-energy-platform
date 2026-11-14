-- eco2mix is 15-min (real-time) or 30-min (definitive) granularity; weather
-- is hourly. Aggregate consumption up to the hour so fct_consumption_weather
-- can join the two on the same grain. Clean rows only.
--
-- ech_physiques_mw is also averaged up to the hour here (not unpivoted
-- into int_energy_production_unpivoted -- it's a grid exchange, not a
-- production source): RTE's sign convention is positive = net export,
-- negative = net import, needed for business question 3 (which regions
-- depend on imports at peak consumption).
select
    code_insee_region,
    date_trunc('hour', date_heure) as observed_hour,
    avg(consommation_mw) as consommation_mw_avg,
    avg(ech_physiques_mw) as ech_physiques_mw_avg
from {{ ref('int_eco2mix_checked') }}
where reject_reason is null
group by 1, 2
