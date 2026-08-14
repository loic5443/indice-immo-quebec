"""Streamlit smoke tests for the gated comparator presentation."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database, save_analysis


class PropertyComparatorUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "ui-comparison.db"
        initialize_database(self.database_path)
        created, _ = create_user("Compte test", "ui@example.test", "motdepasse-solide", self.database_path)
        self.assertTrue(created)
        self.user = authenticate_user("ui@example.test", "motdepasse-solide", self.database_path)
        for name, cash_flow in (("Dossier un", 150), ("Dossier deux", 280)):
            save_analysis(self.user["id"], name, {
                "price": 450_000, "down_payment": 90_000, "rental_income": 2_900,
                "monthly_expenses": 2_650, "cash_flow": cash_flow, "cash_on_cash_return": 2.8,
                "capitalization_rate": 4.9, "debt_service_coverage_ratio": 1.08,
            }, self.database_path)

    def tearDown(self):
        self.temp.cleanup()

    def _app(self, plan):
        from streamlit.testing.v1 import AppTest
        source = f'''
import components.saved_analyses as page
page.DATABASE_PATH = r"{self.database_path}"
page.is_authenticated = lambda: True
page.current_user = lambda: {{"id": {self.user["id"]}, "plan": "{plan}", "role": "user"}}
page.show_saved_analyses()
'''
        return AppTest.from_string(source).run(timeout=20)

    def test_free_account_sees_useful_preview_without_premium_metrics(self):
        app = self._app("free")
        self.assertFalse(app.exception)
        text = " ".join(item.value for item in app.markdown) + " ".join(item.value for item in app.text)
        self.assertIn("APERÇU GRATUIT", text)
        self.assertIn("Flux de trésorerie", text)
        self.assertNotIn("Paiement hypothécaire mensuel", text)

    def test_premium_account_sees_complete_comparison(self):
        app = self._app("premium")
        self.assertFalse(app.exception)
        text = " ".join(item.value for item in app.markdown) + " ".join(item.value for item in app.text)
        self.assertTrue(any("Comparaison complète" in item.value for item in app.success))
        self.assertIn("Paiement hypothécaire mensuel", text)
        self.assertIn("Scénarios sauvegardés", text)


if __name__ == "__main__":
    unittest.main()
