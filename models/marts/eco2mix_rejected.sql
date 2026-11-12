-- Quarantine: every row int_eco2mix_checked flagged, with its reason.
-- Nothing here feeds fct_energy_production or fct_consumption_weather.
select *
from {{ ref('int_eco2mix_checked') }}
where reject_reason is not null
