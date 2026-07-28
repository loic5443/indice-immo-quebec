"""Deterministic validation before an external observation can become public data."""

from datetime import date
from math import isfinite

from domain.market_data import MarketObservation


def validate_observation(observation: MarketObservation) -> list[str]:
    """Return explicit quality failures; callers quarantine rather than silently repair."""
    errors: list[str] = []
    if not isfinite(observation.value):
        errors.append("valeur non numérique")
    if observation.metric == "policy_rate" and not 0 <= observation.value <= 25:
        errors.append("taux directeur hors plage plausible")
    if observation.metric == "policy_rate" and observation.unit != "percent":
        errors.append("unité inattendue")
    if not observation.geography_code or not observation.source_url.startswith("https://"):
        errors.append("provenance ou géographie manquante")
    try:
        date.fromisoformat(observation.observed_at[:10])
    except ValueError:
        errors.append("date d'observation invalide")
    return errors


def freshness_label(observed_at: str, max_age_days: int = 45) -> str:
    try:
        age = (date.today() - date.fromisoformat(observed_at[:10])).days
    except ValueError:
        return "inconnue"
    return "fresh" if age <= max_age_days else "stale"
