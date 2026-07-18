"""Tests for local account security and user-scoped saved analyses."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from data.database import (
    authenticate_user,
    create_user,
    delete_analysis,
    initialize_database,
    list_analyses,
    save_analysis,
    toggle_favorite,
    validate_registration,
)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "immoradar-test.db"
        initialize_database(self.database_path)
        self.analysis_values = {
            "price": 500_000,
            "down_payment": 100_000,
            "rental_income": 3_200,
            "monthly_expenses": 2_960,
            "cash_flow": 240,
            "cash_on_cash_return": 2.88,
            "capitalization_rate": 6.16,
            "debt_service_coverage_ratio": 1.1,
        }

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _create_and_login(self, name: str, email: str, password: str = "motdepasse-solide"):
        created, _ = create_user(name, email, password, self.database_path)
        self.assertTrue(created)
        return authenticate_user(email, password, self.database_path)

    def test_account_creation_hashes_password(self):
        user = self._create_and_login("Alice", "alice@example.com")
        self.assertEqual(user["email"], "alice@example.com")
        with closing(sqlite3.connect(self.database_path)) as connection:
            stored_hash, stored_salt = connection.execute(
                "SELECT password_hash, password_salt FROM users WHERE email = ?", ("alice@example.com",)
            ).fetchone()
        self.assertNotEqual(stored_hash, "motdepasse-solide")
        self.assertTrue(stored_salt)

    def test_login_rejects_wrong_password(self):
        self._create_and_login("Alice", "alice@example.com")
        self.assertIsNone(authenticate_user("alice@example.com", "mauvais-mot-de-passe", self.database_path))

    def test_registration_validation(self):
        errors = validate_registration("A", "invalide", "court", "different")
        self.assertGreaterEqual(len(errors), 3)

    def test_save_and_delete_analysis(self):
        user = self._create_and_login("Alice", "alice@example.com")
        analysis_id = save_analysis(user["id"], "Duplex Alice", self.analysis_values, self.database_path)
        self.assertEqual(len(list_analyses(user["id"], self.database_path)), 1)
        self.assertTrue(delete_analysis(user["id"], analysis_id, self.database_path))
        self.assertEqual(list_analyses(user["id"], self.database_path), [])

    def test_favorites_and_user_data_are_isolated(self):
        alice = self._create_and_login("Alice", "alice@example.com")
        bob = self._create_and_login("Bob", "bob@example.com")
        alice_analysis = save_analysis(alice["id"], "Duplex Alice", self.analysis_values, self.database_path)
        bob_analysis = save_analysis(bob["id"], "Triplex Bob", self.analysis_values, self.database_path)

        self.assertTrue(toggle_favorite(alice["id"], alice_analysis, self.database_path))
        self.assertTrue(list_analyses(alice["id"], self.database_path)[0]["is_favorite"])
        self.assertEqual(list_analyses(bob["id"], self.database_path)[0]["property_name"], "Triplex Bob")
        self.assertFalse(toggle_favorite(alice["id"], bob_analysis, self.database_path))
        self.assertFalse(delete_analysis(alice["id"], bob_analysis, self.database_path))
        self.assertEqual(len(list_analyses(bob["id"], self.database_path)), 1)


if __name__ == "__main__":
    unittest.main()
