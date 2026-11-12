-- Staging: no row is removed here (TP3 staging rule). The weather columns
-- already arrive typed (dlt had no cross-source conflict to force text on,
-- unlike eco2mix -- see ADR 0002), but we try_cast anyway: if Open-Meteo
-- ever sends a string where a number belongs, this returns NULL instead of
-- breaking the model.
select
    code_insee_region,
    region_name,
    time as observed_at,
    try_cast(temperature_2m as double) as temperature_c,
    try_cast(wind_speed_10m as double) as wind_speed_kmh,
    try_cast(shortwave_radiation as double) as shortwave_radiation_wm2,
    try_cast(cloud_cover as double) as cloud_cover_pct,
    _dlt_load_id,
    _dlt_id
from {{ source('raw', 'weather_hourly') }}
