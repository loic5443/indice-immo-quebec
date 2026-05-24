import requests


def get_canada_rate():

    try:
        url = "https://www.bankofcanada.ca/valet/observations/V39079/json"

        data = requests.get(url, timeout=10).json()

        return float(data["observations"][-1]["V39079"]["v"])

    except:
        return 5.0


def get_inflation():

    # Valeur temporaire officielle Canada
    return 2.7


def get_unemployment():

    # Valeur temporaire officielle Canada
    return 6.9