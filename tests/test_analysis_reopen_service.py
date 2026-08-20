"""Regression tests for reopening a saved analysis as a new local draft."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data.database import authenticate_user, create_user, initialize_database, save_analysis
from services.analysis_reopen_service import AnalysisReopenAccessError, prepare_reopen_draft


class AnalysisReopenServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "reopen.sqlite"
        initialize_database(self.database_path)
        self.alice = self._user("Alice", "alice@example.test")
        self.bob = self._user("Bob", "bob@example.test")
        self.analysis_id = save_analysis(self.alice["id"], "Dossier de test", {
            "price": 500_000,
            "down_payment": 100_000,
            "rental_income": 2_900,
            "monthly_expenses": 2_400,
            "cash_flow": 500,
            "cash_on_cash_return": 4.0,
            "capitalization_rate": 5.0,
            "debt_service_coverage_ratio": 1.15,
            "financial_inputs": {
                "price": 500_000,
                "down_payment": 100_000,
                "annual_interest_rate": 4.85,
                "amortization_years": 25,
                "rental_income_monthly": 2_900,
                "_analysis_objective": "Investir et louer",
                "_property_type": "Duplex",
                "mortgage_renewal_date": "2027-06-15",
            },
            "immovalue": {"available": False, "subject": {"asking_price": 525_000}},
            "official_role_snapshot": {"total_value": 450_000, "source": "Source officielle"},
        }, self.database_path, profile="Investisseur locatif")

    def tearDown(self):
        self.temp.cleanup()

    def _user(self, name, email):
        created, _ = create_user(name, email, "Motdepasse1", self.database_path)
        self.assertTrue(created)
        return authenticate_user(email, "Motdepasse1", self.database_path)

    def test_restores_only_editable_inputs_and_declared_subject_fields(self):
        draft = prepare_reopen_draft(self.alice["id"], self.analysis_id, self.database_path)
        self.assertEqual(draft["owner_id"], self.alice["id"])
        self.assertEqual(draft["property_name"], "Dossier de test")
        self.assertEqual(draft["property_type"], "Duplex")
        self.assertEqual(draft["objective"], "Investir et louer")
        self.assertEqual(draft["asking_price"], 525_000)
        self.assertEqual(draft["mortgage_renewal_date"], "2027-06-15")
        self.assertEqual(draft["financial_values"]["property_price"], 500_000)
        self.assertEqual(draft["financial_values"]["mortgage_rate"], 4.85)
        self.assertNotIn("official_role_snapshot", draft)
        self.assertNotIn("address", draft)

    def test_refuses_another_users_dossier_without_exposing_it(self):
        with self.assertRaises(AnalysisReopenAccessError):
            prepare_reopen_draft(self.bob["id"], self.analysis_id, self.database_path)

    def test_reopen_payload_starts_an_empty_address_form_without_recalculation(self):
        payload = prepare_reopen_draft(self.alice["id"], self.analysis_id, self.database_path)
        source = (
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            "original_database_path = page.DATABASE_PATH\n"
            "original_is_authenticated = page.is_authenticated\n"
            "original_current_user = page.current_user\n"
            "try:\n"
            f"    page.DATABASE_PATH = Path({str(self.database_path)!r})\n"
            "    page.is_authenticated = lambda: True\n"
            "    page.current_user = lambda: {'id': 1, 'user_type': 'Investisseur locatif'}\n"
            f"    st.session_state['analysis_reopen_pending'] = {payload!r}\n"
            "    page.show_property_analysis()\n"
            "finally:\n"
            "    page.DATABASE_PATH = original_database_path\n"
            "    page.is_authenticated = original_is_authenticated\n"
            "    page.current_user = original_current_user\n"
        )
        app = AppTest.from_string(source).run(timeout=20)
        self.assertEqual(app.text_input(key="workflow_property_name").value, "Dossier de test")
        self.assertEqual(app.selectbox(key="workflow_property_type").value, "Duplex")
        self.assertEqual(app.number_input(key="iv_asking").value, 525_000)
        self.assertEqual(app.session_state["mortgage_renewal_date"], date(2027, 6, 15))
        self.assertEqual(app.session_state["property_price"], 500_000)
        self.assertEqual(app.text_input(key="address_form_city").value, "")
        self.assertEqual(app.text_input(key="address_form_postal").value, "")
        self.assertNotIn("address_form_lookup", app.session_state)
        self.assertTrue(any("aucune recherche publique" in item.value for item in app.success))


if __name__ == "__main__":
    unittest.main()
