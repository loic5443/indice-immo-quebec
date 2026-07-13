import requests


def get_canada_rate():
    """Retrieve the latest Bank of Canada policy rate, with a safe fallback."""
    try:
        response = requests.get(
            "https://www.bankofcanada.ca/valet/observations/V39079/json", timeout=10
        )
        response.raise_for_status()
        return float(response.json()["observations"][-1]["V39079"]["v"]), True
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return 5.0, False


def get_inflation():
    return 2.7


def get_unemployment():
    return 6.9
