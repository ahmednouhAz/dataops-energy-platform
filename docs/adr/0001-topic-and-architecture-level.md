# ADR 0001 — Topic and architecture level

## Decision
- Topic 2, Energy: eCO2mix regional data + Open-Meteo weather.
- Architecture level 1: ELT warehouse (dlt → DuckDB → dbt). Designed so level 2 (Parquet/Iceberg on MinIO) can be added later.
- Orchestration with Prefect 3.

## Why
- Neither source needs an API key, and both have years of history: backfilling to more than 1M rows is easy (the eCO2mix regional dataset alone has about 2.9M rows).
- I work alone: level 1 and Prefect keep the infrastructure small enough to master completely.

## Alternatives rejected
- Bikes (GBFS): no history to backfill, so reaching 1M rows would take weeks of collection.
- Air quality (OpenAQ): needs an API key and has rate limits.
- Airflow: the industry standard, but heavy (scheduler, web server, metadata database) for a solo project. 