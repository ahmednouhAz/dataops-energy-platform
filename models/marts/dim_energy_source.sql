select
    energy_source,
    label,
    is_renewable
from {{ ref('energy_sources') }}
