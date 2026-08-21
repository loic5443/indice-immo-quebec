"""Tests for local-only Premium interest preferences."""

import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database
from services.premium_interest_service import has_premium_interest, set_premium_interest


class PremiumInterestServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "premium-interest.sqlite"
        initialize_database(self.database_path)
        self.alice = self._create_user("Alice", "alice@example.test")
        self.bob = self._create_user("Bob", "bob@example.test")

    def tearDown(self):
        self.temp.cleanup()

    def _create_user(self, name: str, email: str) -> dict:
        created, _ = create_user(name, email, "motdepasse-solide", self.database_path)
        self.assertTrue(created)
        user = authenticate_user(email, "motdepasse-solide", self.database_path)
        self.assertIsNotNone(user)
        return user

    def test_interest_is_local_and_isolated_between_accounts(self):
        set_premium_interest(self.alice["id"], True, self.database_path)
        self.assertTrue(has_premium_interest(self.alice["id"], self.database_path))
        self.assertFalse(has_premium_interest(self.bob["id"], self.database_path))

    def test_interest_can_be_withdrawn_without_external_delivery(self):
        set_premium_interest(self.alice["id"], True, self.database_path)
        set_premium_interest(self.alice["id"], False, self.database_path)
        self.assertFalse(has_premium_interest(self.alice["id"], self.database_path))


if __name__ == "__main__":
    unittest.main()
