"""Load the CI fixtures into ci.duckdb's raw schema, mimicking the column
types dlt actually produces (date_heure/time as real timestamps, every
measurement column as text -- see pipeline/sources/eco2mix.py's
TEXT_COLUMN_HINTS), so dbt build --target ci behaves like a real dlt load.

Run from the repo root:
    python tests/load_fixtures.py
"""
import duckdb

CI_DUCKDB_PATH = "ci.duckdb"


def main():
    con = duckdb.connect(CI_DUCKDB_PATH)
    con.execute("create schema if not exists raw")

    con.execute("""
        create or replace table raw.eco2mix_regional as
        select
            code_insee_region::varchar as code_insee_region,
            libelle_region::varchar as libelle_region,
            nature::varchar as nature,
            date::varchar as date,
            heure::varchar as heure,
            date_heure::timestamptz as date_heure,
            consommation::varchar as consommation,
            thermique::varchar as thermique,
            nucleaire::varchar as nucleaire,
            eolien::varchar as eolien,
            solaire::varchar as solaire,
            hydraulique::varchar as hydraulique,
            pompage::varchar as pompage,
            bioenergies::varchar as bioenergies,
            ech_physiques::varchar as ech_physiques,
            stockage_batterie::varchar as stockage_batterie,
            destockage_batterie::varchar as destockage_batterie,
            -- Not in the fixture (it only mimics the real-time dataset's
            -- shape, which doesn't have these -- ADR 0002); dlt's explicit
            -- column hints still materialize them as null text columns in
            -- the real raw table, so stg_eco2mix_regional can rely on them
            -- existing. Match that here.
            cast(null as varchar) as eolien_terrestre,
            cast(null as varchar) as eolien_offshore,
            'fixture' as _dlt_load_id,
            cast(row_number() over () as varchar) as _dlt_id
        from read_csv('tests/fixtures/eco2mix_sample.csv', all_varchar = true)
    """)
    n = con.execute("select count(*) from raw.eco2mix_regional").fetchone()[0]
    print(f"Loaded {n} rows into raw.eco2mix_regional")

    con.execute("""
        create or replace table raw.weather_hourly as
        select
            code_insee_region::varchar as code_insee_region,
            region_name::varchar as region_name,
            time::timestamptz as time,
            temperature_2m::double as temperature_2m,
            wind_speed_10m::double as wind_speed_10m,
            shortwave_radiation::double as shortwave_radiation,
            cloud_cover::bigint as cloud_cover,
            'fixture' as _dlt_load_id,
            cast(row_number() over () as varchar) as _dlt_id
        from read_csv('tests/fixtures/weather_sample.csv', all_varchar = true)
    """)
    n = con.execute("select count(*) from raw.weather_hourly").fetchone()[0]
    print(f"Loaded {n} rows into raw.weather_hourly")

    con.close()


if __name__ == "__main__":
    main()
