"""dlt source for eCO2mix regional data.

Two upstream datasets cover different periods and do NOT share one JSON
schema (see docs/adr/0002-source-exploration.md): the definitive dataset
stops where the real-time one starts. We pick the right dataset per date
and force every measurement column to text at load time, same philosophy
as TP3's `all_varchar = true`: raw keeps the value exactly as the API sent
it, typing is a staging decision (step 4), not a loading decision.
"""
import dlt
import requests

BASE = "https://odre.opendatasoft.com/api/explore/v2.1"
DEFINITIVE_ID = "eco2mix-regional-cons-def"
REALTIME_ID = "eco2mix-regional-tr"
CUTOVER_DATE = "2026-08-31"  # last day of history in the definitive dataset

PAGE_SIZE = 100  # Opendatasoft caps /records at 100 rows per page

# Columns that are numbers in one dataset and strings in the other (or vice
# versa) -- see ADR 0002. Forcing all of them to text keeps raw.eco2mix_regional
# consistent no matter which of the two datasets a row came from.
MEASUREMENT_COLUMNS = [
    "consommation", "thermique", "nucleaire", "eolien", "solaire",
    "hydraulique", "pompage", "bioenergies", "ech_physiques",
    "stockage_batterie", "destockage_batterie",
    "eolien_terrestre", "eolien_offshore",
    "tco_thermique", "tch_thermique", "tco_nucleaire", "tch_nucleaire",
    "tco_eolien", "tch_eolien", "tco_solaire", "tch_solaire",
    "tco_hydraulique", "tch_hydraulique", "tco_bioenergies", "tch_bioenergies",
]
TEXT_COLUMN_HINTS = {col: {"data_type": "text"} for col in MEASUREMENT_COLUMNS}


def _fetch_records(dataset_id, start_date, end_date):
    """Page through one dataset's /records endpoint for [start_date, end_date)."""
    url = f"{BASE}/catalog/datasets/{dataset_id}/records"
    where = f'date_heure >= "{start_date}" and date_heure < "{end_date}"'
    offset = 0
    while True:
        resp = requests.get(
            url,
            params={
                "where": where,
                "limit": PAGE_SIZE,
                "offset": offset,
                "order_by": "date_heure asc",
            },
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json()["results"]
        if not results:
            break
        yield from results
        offset += PAGE_SIZE


@dlt.resource(
    name="eco2mix_regional",
    write_disposition="merge",
    primary_key=("code_insee_region", "date_heure"),
    columns=TEXT_COLUMN_HINTS,
)
def eco2mix_regional(start_date: str, end_date: str):
    """Yield eco2mix rows for [start_date, end_date), switching dataset at the cutover."""
    if end_date <= CUTOVER_DATE:
        yield from _fetch_records(DEFINITIVE_ID, start_date, end_date)
    elif start_date >= CUTOVER_DATE:
        yield from _fetch_records(REALTIME_ID, start_date, end_date)
    else:
        yield from _fetch_records(DEFINITIVE_ID, start_date, CUTOVER_DATE)
        yield from _fetch_records(REALTIME_ID, CUTOVER_DATE, end_date)


@dlt.source
def eco2mix_source(start_date: str, end_date: str):
    return eco2mix_regional(start_date, end_date)
