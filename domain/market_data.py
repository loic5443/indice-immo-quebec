"""Typed, source-traceable observations used by the public markets experience."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MarketObservation:
    """One observed value, never an estimate of a property or a city."""

    source_id: str
    metric: str
    value: float
    unit: str
    geography_code: str
    observed_at: str
    retrieved_at: str
    source_url: str
    classification: str = "observed"
    published_at: str | None = None
    quality_status: str = "valid"
    freshness: str = "fresh"

    def to_snapshot(self) -> dict[str, Any]:
        return asdict(self)
