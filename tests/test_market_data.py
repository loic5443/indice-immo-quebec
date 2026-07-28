"""Local tests for the official-data foundation; no network calls are made."""

import tempfile
import unittest
from pathlib import Path

from data.database import initialize_database
from domain.market_data import MarketObservation
from providers.official_data import ProviderError
from repositories.market_data_repository import MarketDataRepository
from services.market_data_service import cached_policy_rate, refresh_source


class FakeProvider:
    source_id = "bank_of_canada_valet"

    def __init__(self, observations=None, error=None):
        self.observations = observations or []
        self.error = error

    def fetch(self):
        if self.error:
            raise self.error
        return self.observations


def observation(value=4.5, observed_at="2026-07-20"):
    return MarketObservation("bank_of_canada_valet", "policy_rate", value, "percent", "CA", observed_at,
                             "2026-07-28T12:00:00Z", "https://www.bankofcanada.ca/valet/observations/V39079/json")


class MarketDataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "market.db"
        initialize_database(self.database)

    def tearDown(self):
        self.directory.cleanup()

    def test_valid_value_is_cached_with_provenance_and_deduplicated(self):
        provider = FakeProvider([observation()])
        self.assertEqual(len(refresh_source(str(self.database), provider)), 1)
        self.assertEqual(len(refresh_source(str(self.database), provider)), 1)
        cached = cached_policy_rate(str(self.database))
        self.assertEqual(cached["value"], 4.5)
        self.assertEqual(cached["source_id"], "bank_of_canada_valet")
        self.assertEqual(cached["quality_status"], "valid")

    def test_invalid_value_is_quarantined_and_not_served(self):
        refresh_source(str(self.database), FakeProvider([observation(99)]))
        self.assertIsNone(cached_policy_rate(str(self.database)))
        repository = MarketDataRepository(self.database)
        connection = repository._connect()
        row = connection.execute("SELECT quality_status FROM market_observations").fetchone()
        connection.close()
        self.assertEqual(row[0], "quarantined")

    def test_failed_refresh_keeps_last_valid_cache(self):
        refresh_source(str(self.database), FakeProvider([observation()]))
        refresh_source(str(self.database), FakeProvider(error=ProviderError("offline")))
        self.assertEqual(cached_policy_rate(str(self.database))["value"], 4.5)

    def test_public_market_page_does_not_import_simulated_data_or_fallback_value(self):
        source = (Path(__file__).parents[1] / "components" / "markets.py").read_text(encoding="utf-8")
        legacy = (Path(__file__).parents[1] / "data" / "real_data.py").read_text(encoding="utf-8")
        self.assertNotIn("simulated_data", source)
        self.assertNotIn("SIMULATED", source)
        self.assertNotIn("return 5.0", legacy)
