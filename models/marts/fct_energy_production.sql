{#
    dbt requires on_schema_change to be 'append_new_columns' or 'fail'
    once a model contract is enforced (found by running this:
    'sync_all_columns' is rejected outright). 'fail' is also the more
    correct choice for a contracted model -- the contract's whole point
    is that a shape change should be a loud build failure, not something
    silently synced into the table underneath it.
#}
{{
    config(
        materialized='incremental',
        unique_key=['code_insee_region', 'date_heure', 'energy_source'],
        on_schema_change='fail'
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
