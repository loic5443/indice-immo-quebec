"""Focused regressions for the owner-scoped saved-property comparator."""

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database, save_analysis
from services.entitlements_service import can_use
from services.property_comparison_service import ComparisonAccessError, compare_saved_analyses


class PropertyComparisonServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "comparison.db"
        initialize_database(self.database_path)
        self.alice = self._user("Alice", "alice@example.test")
        self.bob = self._user("Bob", "bob@example.test")
        self.analysis_a = self._analysis(self.alice["id"], "Dossier A", 500_000, 220, 68, "ImmoEngine 1.0")
        self.analysis_b = self._analysis(self.alice["id"], "Dossier B", 510_000, 360, 74, "ImmoEngine 2.0")
        self.other_analysis = self._analysis(self.bob["id"], "Dossier privé", 400_000, 550, 82, "ImmoEngine 2.0")

    def tearDown(self):
        self.temp.cleanup()

    def _user(self, name, email):
        created, _ = create_user(name, email, "motdepasse-solide", self.database_path)
        self.assertTrue(created)
        return authenticate_user(email, "motdepasse-solide", self.database_path)

    def _analysis(self, user_id, name, price, cash_flow, score, engine_version):
        values = {
            "price": price,
            "down_payment": 100_000,
            "rental_income": 3_100,
            "monthly_expenses": 2_700,
            "cash_flow": cash_flow,
            "cash_on_cash_return": 3.4,
            "capitalization_rate": 5.2,
            "debt_service_coverage_ratio": 1.18,
            "financial_inputs": {"property_type": "Duplex"},
            "scenarios": [{"name": "Scénario de base", "financial": {"monthly_payment": 2_100, "cash_flow_monthly": cash_flow}}],
            "resilience": {"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": cash_flow - 180}}]},
            "immovalue": {"available": True, "estimated_value": price - 10_000, "low": price - 30_000, "high": price + 10_000, "confidence": 62},
        }
        analysis_id = save_analysis(user_id, name, values, self.database_path, profile="Investisseur locatif")
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute(
                "UPDATE analyses SET immo_score=?, confidence_index=?, engine_version=?, official_role_snapshot_json=? WHERE id=?",
                (score, 70, engine_version, json.dumps({"total_value": price - 55_000, "role_year": 2026, "source": "Source officielle"}), analysis_id),
            )
        return analysis_id

    def test_compares_only_saved_snapshots_and_marks_versions(self):
        result = compare_saved_analyses(self.alice["id"], self.analysis_a, self.analysis_b, self.database_path)
        self.assertEqual((result["a"]["name"], result["b"]["name"]), ("Dossier A", "Dossier B"))
        self.assertEqual(result["a"]["cash_flow"], 220)
        self.assertEqual(result["a"]["municipal_value"], 445_000)
        self.assertEqual(result["b"]["rate_up_cash_flow"], 180)
        self.assertTrue(result["engine_versions_differ"])
        self.assertIn("mieux alignée", result["conclusion"])
        self.assertTrue(any(item["key"] == "cash_flow" and item["relation"] == "avantage_b" for item in result["indicators"]))

    def test_rejects_cross_user_and_duplicate_selection_without_disclosure(self):
        with self.assertRaises(ComparisonAccessError):
            compare_saved_analyses(self.alice["id"], self.analysis_a, self.other_analysis, self.database_path)
        with self.assertRaises(ValueError):
            compare_saved_analyses(self.alice["id"], self.analysis_a, self.analysis_a, self.database_path)

    def test_missing_values_are_not_turned_into_zeroes(self):
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute("UPDATE analyses SET immo_score=NULL, confidence_index=NULL WHERE id=?", (self.analysis_a,))
        result = compare_saved_analyses(self.alice["id"], self.analysis_a, self.analysis_b, self.database_path)
        score = next(item for item in result["indicators"] if item["key"] == "score")
        self.assertEqual(score["relation"], "non_comparable")
        self.assertIsNone(score["a"])
        self.assertTrue(any("Score ImmoRadar" in item for item in result["checks"]["a"]))

    def test_advanced_comparison_entitlement_is_centralized(self):
        self.assertFalse(can_use({"plan": "free", "role": "user"}, "advanced_comparisons"))
        self.assertTrue(can_use({"plan": "premium", "role": "user"}, "advanced_comparisons"))
        self.assertTrue(can_use({"plan": "free", "role": "admin"}, "advanced_comparisons"))


if __name__ == "__main__":
    unittest.main()
