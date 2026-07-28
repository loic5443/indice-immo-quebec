"""Interfaces and official providers. No credentials or simulated values are used here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

import requests

from domain.market_data import MarketObservation


class ProviderError(RuntimeError):
    """An official source could not be retrieved or its response was unusable."""


class OfficialDataProvider(Protocol):
    source_id: str

    def fetch(self) -> list[MarketObservation]: ...


@dataclass
class BankOfCanadaPolicyRateProvider:
    """Fetch the Bank of Canada's V39079 policy rate from its public Valet API."""

    source_id: str = "bank_of_canada_valet"
    request_get: Callable[..., object] = requests.get
    url: str = "https://www.bankofcanada.ca/valet/observations/V39079/json"

    def fetch(self) -> list[MarketObservation]:
        try:
            response = self.request_get(self.url, timeout=10)
            response.raise_for_status()
            observations = response.json()["observations"]
            latest = observations[-1]
            value = float(latest["V39079"]["v"])
            observed_at = str(latest["d"])
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
            raise ProviderError("Réponse Banque du Canada indisponible ou incompatible.") from error
        return [MarketObservation(
            source_id=self.source_id, metric="policy_rate", value=value, unit="percent",
            geography_code="CA", observed_at=observed_at,
            retrieved_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            source_url=self.url,
        )]
