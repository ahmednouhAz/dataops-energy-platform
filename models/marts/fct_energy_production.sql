{{
    config(
        materialized='incremental',
        unique_key=['code_insee_region', 'date_heure', 'energy_source'],
        on_schema_change='sync_all_columns'
    )
}}

select
    p.code_insee_region,
    p.date_heure,
    p.energy_source,
    p.production_mw
from {{ ref('int_energy_production_unpivoted') }} as p

{% if is_incremental() %}
where p.date_heure > (select max(prev.date_heure) from {{ this }} as prev)
{% endif %}
