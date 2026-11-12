-- fct_energy_production's key is a combination of 3 columns, which the
-- built-in `unique` generic test can't check on its own (it only takes one
-- column). A data test passes when it returns no rows.
select code_insee_region, date_heure, energy_source, count(*) as n
from {{ ref('fct_energy_production') }}
group by 1, 2, 3
having count(*) > 1
