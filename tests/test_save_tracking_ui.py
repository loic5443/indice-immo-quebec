"""Regression for enabling local dossier tracking immediately after saving."""

import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database
from services.dossier_tracking_service import tracked_dossier_fingerprints
from streamlit.testing.v1 import AppTest


class SaveTrackingUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "save-tracking.sqlite"
        initialize_database(self.database_path)
        created, _ = create_user("Compte test", "save-track@example.test", "Motdepasse1", self.database_path)
        self.assertTrue(created)
        self.user = authenticate_user("save-track@example.test", "Motdepasse1", self.database_path)
        self.user["plan"] = "premium"

    def tearDown(self):
        self.temp.cleanup()

    def test_saved_premium_dossier_can_start_local_follow_immediately(self):
        import components.property_analysis as page

        original_database_path = page.DATABASE_PATH
        original_is_authenticated = page.is_authenticated
        original_current_user = page.current_user
        original_save_analysis = page.save_analysis
        source = (
            "from pathlib import Path\n"
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "from data.database import save_analysis as persist_analysis\n"
            f"page.DATABASE_PATH = Path({str(self.database_path)!r})\n"
            "page.is_authenticated = lambda: True\n"
            f"page.current_user = lambda: {self.user!r}\n"
            f"page.save_analysis = lambda user_id, property_name, values, profile, engine_result: persist_analysis(user_id, property_name, values, Path({str(self.database_path)!r}), profile, engine_result)\n"
            "inputs = PropertyInputs(price=400000, down_payment=80000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3000, school_taxes_annual=300, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=2500, other_expenses_monthly=200)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Investisseur locatif')\n"
        )
        try:
            app = AppTest.from_string(source).run(timeout=20)
            app.text_input(key="saved_property_name").set_value("Dossier de suivi").run(timeout=20)
            app.button(key="save_analysis").click().run(timeout=20)
            self.assertIn("Activer le suivi de ce dossier", [button.label for button in app.button])
            app.button(key="activate_saved_dossier_tracking").click().run(timeout=20)
            self.assertTrue(tracked_dossier_fingerprints(self.user["id"], self.database_path))
            self.assertIn("Suivi de ce dossier actif", [button.label for button in app.button])
            self.assertTrue(any("Le suivi est actif" in item.value for item in app.caption))
        finally:
            page.DATABASE_PATH = original_database_path
            page.is_authenticated = original_is_authenticated
            page.current_user = original_current_user
            page.save_analysis = original_save_analysis


if __name__ == "__main__":
    unittest.main()
