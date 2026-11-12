"""Explore the eCO2mix regional API: find the real-time dataset id,
inspect columns, types and nulls on a small sample."""
import requests

BASE = "https://odre.opendatasoft.com/api/explore/v2.1"
DEFINITIVE_ID = "eco2mix-regional-cons-def"


def find_realtime_dataset():
    """Search the catalog for eco2mix datasets to confirm the real-time id."""
    url = f"{BASE}/catalog/datasets"
    resp = requests.get(url, params={"where": 'search(dataset_id, "eco2mix")', "limit": 20})
    resp.raise_for_status()
    results = resp.json()["results"]
    print(f"Found {len(results)} dataset(s) matching 'eco2mix':")
    for d in results:
        print(f"  - {d['dataset_id']}")
    return results


def inspect_sample(dataset_id, n=5):
    """Print total row count and the raw fields/types of a small sample."""
    url = f"{BASE}/catalog/datasets/{dataset_id}/records"
    resp = requests.get(url, params={"limit": n})
    resp.raise_for_status()
    data = resp.json()
    print(f"\n--- {dataset_id} ---")
    print(f"total_count = {data['total_count']}")
    sample = data["results"][0]
    print(f"{len(sample)} fields in one record:")
    for key, value in sample.items():
        print(f"  {key:25s} = {value!r:30}  (python type: {type(value).__name__})")


def check_date_range(dataset_id):
    """Find the earliest and latest date_heure available, by sorting."""
    url = f"{BASE}/catalog/datasets/{dataset_id}/records"
    oldest = requests.get(url, params={"limit": 1, "order_by": "date_heure asc"}).json()
    newest = requests.get(url, params={"limit": 1, "order_by": "date_heure desc"}).json()
    print(f"  oldest date_heure = {oldest['results'][0]['date_heure']}")
    print(f"  newest date_heure = {newest['results'][0]['date_heure']}")


if __name__ == "__main__":
    find_realtime_dataset()
    inspect_sample(DEFINITIVE_ID)
    check_date_range(DEFINITIVE_ID)

    REALTIME_ID = "eco2mix-regional-tr"
    inspect_sample(REALTIME_ID)
    check_date_range(REALTIME_ID)
