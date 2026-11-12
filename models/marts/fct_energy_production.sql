{{
    config(
        materialized='incremental',
        unique_key=['code_insee_region', 'date_heure', 'energy_source'],
        on_schema_change='sync_all_columns'
    )
}}

select
    code_insee_region,
    date_heure,
    energy_source,
    production_mw
from {{ ref('int_energy_production_unpivoted') }}

{% if is_incremental() %}
where date_heure > (select max(date_heure) from {{ this }})
{% endif %}
