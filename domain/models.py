"""Framework-agnostic models shared by ImmoRadar services."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfile:
    """Non-sensitive profile choices used to tailor future product flows."""

    user_type: str = "Investisseur"
    investment_horizon: str = "2 à 5 ans"
    risk_tolerance: str = "Modéré"


@dataclass(frozen=True)
class ImmoEngineMetadata:
    """Traceability metadata; this engine does not estimate a property value."""

    version: str
    data_provenance: str
