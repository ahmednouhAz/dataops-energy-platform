select
    c.code_insee_region,
    c.observed_hour,
    c.consommation_mw_avg,
    w.temperature_c,
    w.wind_speed_kmh,
    w.cloud_cover_pct
from {{ ref('int_consumption_hourly') }} as c
left join {{ ref('stg_weather_hourly') }} as w
    on c.code_insee_region = w.code_insee_region
    and c.observed_hour = w.observed_at
