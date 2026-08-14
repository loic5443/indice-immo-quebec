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
from domain.immoengine import evaluate_immoengine
from calculations.real_estate import PropertyInputs, calculate_analysis
from migrations.runner import applied_migrations, apply_migrations
from services.auth_service import validate_login_submission


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

    def test_empty_login_has_precise_validation_but_invalid_credentials_stay_generic(self):
        self.assertEqual(validate_login_submission("", ""), ["Le courriel est requis.", "Le mot de passe est requis."])
        self.assertEqual(validate_login_submission("alice@example.com", "incorrect"), [])

    def test_registration_validation(self):
        errors = validate_registration("A", "invalide", "court", "different")
        self.assertGreaterEqual(len(errors), 3)

    def test_versioned_migrations_add_profile_and_engine_metadata(self):
        self.assertEqual(applied_migrations(self.database_path), ["0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009", "0010", "0011", "0012", "0013", "0014", "0015", "0016", "0017", "0018", "0019", "0020", "0021"])
        with closing(sqlite3.connect(self.database_path)) as connection:
            user_columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
            analysis_columns = {row[1] for row in connection.execute("PRAGMA table_info(analyses)")}
        self.assertTrue({"user_type", "investment_horizon", "risk_tolerance"}.issubset(user_columns))
        self.assertTrue({"engine_version", "data_provenance", "immo_score", "confidence_index", "engine_verdict", "immodna_json", "financial_inputs_json", "scenarios_json", "resilience_json", "market_context_json"}.issubset(analysis_columns))

    def test_save_and_delete_analysis(self):
        user = self._create_and_login("Alice", "alice@example.com")
        inputs = PropertyInputs(
            price=500_000, down_payment=100_000, annual_interest_rate=5.0, amortization_years=25,
            municipal_taxes_annual=3_600, school_taxes_annual=400, insurance_monthly=100,
            condo_fees_monthly=0, rental_income_monthly=3_200, other_expenses_monthly=200,
        )
        engine_result = evaluate_immoengine(inputs, calculate_analysis(inputs), "Investisseur locatif")
        enriched_values = {
            **self.analysis_values,
            "financial_inputs": {"vacancy_rate_pct": 3.0},
            "scenarios": [{"name": "Scénario de base"}],
            "resilience": {"status": "sensible"},
        }
        analysis_id = save_analysis(
            user["id"], "Duplex Alice", enriched_values, self.database_path,
            profile="Investisseur locatif", engine_result=engine_result,
        )
        saved = list_analyses(user["id"], self.database_path)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["engine_version"], "ImmoEngine 1.1.0-financial-scenarios")
        self.assertIn("aucune estimation de valeur", saved[0]["data_provenance"])
        self.assertEqual(saved[0]["user_profile"], "Investisseur locatif")
        self.assertEqual(saved[0]["immo_score"], engine_result.score)
        self.assertEqual(saved[0]["engine_verdict"], engine_result.verdict)
        self.assertIn("vacancy_rate_pct", saved[0]["financial_inputs_json"])
        self.assertIn("Scénario de base", saved[0]["scenarios_json"])
        self.assertTrue(delete_analysis(user["id"], analysis_id, self.database_path))

    def test_saved_analysis_keeps_external_context_separate_from_engine(self):
        user = self._create_and_login("Context", "context@example.com")
        analysis_id = save_analysis(user["id"], "Context", self.analysis_values | {
            "market_context": [{"source_id": "bank_of_canada_valet", "metric": "policy_rate", "value": 4.5}],
        }, self.database_path)
        saved = list_analyses(user["id"], self.database_path)[0]
        self.assertEqual(saved["id"], analysis_id)
        self.assertIn("bank_of_canada_valet", saved["market_context_json"])

    def test_migrations_preserve_an_existing_legacy_database(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as connection, connection:
            connection.executescript(
                """CREATE TABLE users (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL, password_salt TEXT NOT NULL,
                plan TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE analyses (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, property_name TEXT NOT NULL,
                created_at TEXT NOT NULL, price REAL NOT NULL, down_payment REAL NOT NULL,
                rental_income REAL NOT NULL, monthly_expenses REAL NOT NULL, cash_flow REAL NOT NULL,
                cash_on_cash_return REAL NOT NULL, capitalization_rate REAL NOT NULL,
                debt_service_coverage_ratio REAL NOT NULL, is_favorite INTEGER NOT NULL DEFAULT 0);"""
            )
            connection.execute(
                "INSERT INTO users VALUES (1, 'Ancien compte', 'ancien@example.com', 'hash', 'salt', 'free', '2026-01-01')"
            )
        self.assertEqual(apply_migrations(legacy_path), ["0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009", "0010", "0011", "0012", "0013", "0014", "0015", "0016", "0017", "0018", "0019", "0020", "0021"])
        with closing(sqlite3.connect(legacy_path)) as connection:
            profile = connection.execute(
                "SELECT user_type, investment_horizon, risk_tolerance FROM users WHERE id = 1"
            ).fetchone()
        self.assertEqual(profile, ("Investisseur locatif", "2 à 5 ans", "Modéré"))

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
