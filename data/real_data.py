"""Backward-compatible access to the official-data cache; never returns a fictitious fallback."""

from data.database import DATABASE_PATH
from services.market_data_service import cached_policy_rate


def get_canada_policy_rate() -> tuple[float | None, bool]:
    """Return the cached official rate, or ``None`` when it is unavailable."""
    observation = cached_policy_rate(str(DATABASE_PATH))
    return (float(observation["value"]), True) if observation else (None, False)
