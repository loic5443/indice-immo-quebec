"""External data sources. Each value reports whether the live request succeeded."""

import requests


def get_canada_policy_rate() -> tuple[float, bool]:
    """Fetch the latest Bank of Canada policy rate; never expose credentials."""
    try:
        response = requests.get(
            "https://www.bankofcanada.ca/valet/observations/V39079/json", timeout=10
        )
        response.raise_for_status()
        return float(response.json()["observations"][-1]["V39079"]["v"]), True
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return 5.0, False
