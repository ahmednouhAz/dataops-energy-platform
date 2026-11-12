"""A tiny retry wrapper for transient network errors.

Found empirically during step 10's backfill: Open-Meteo occasionally resets
the connection mid-run when called for many regions back to back. Retrying
a plain GET a couple of times with a short delay is enough; this is not a
replacement for the real retry/alerting Prefect will do per-task in step 12
-- just enough that a multi-hour backfill doesn't die on one flaky request.
"""
import time

import requests


def get_with_retries(url, params=None, timeout=30, attempts=3, backoff_seconds=2):
    """requests.get with a few retries on a transient connection error."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return requests.get(url, params=params, timeout=timeout)
        except requests.exceptions.RequestException as error:
            last_error = error
            if attempt < attempts:
                print(f"    request failed ({error}); retrying in {backoff_seconds}s ({attempt}/{attempts})")
                time.sleep(backoff_seconds)
    raise last_error
