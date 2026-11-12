select
    code_insee_region,
    region_name,
    city as representative_city,
    latitude,
    longitude
from {{ ref('regions') }}
