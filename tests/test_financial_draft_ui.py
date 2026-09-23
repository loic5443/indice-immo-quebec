"""A signed-in analysis draft retains submitted financial inputs across sessions."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import components.property_analysis as property_analysis
from data.database import authenticate_user, create_user, initialize_database
from services.analysis_workflow import load_draft, save_draft


class FinancialDraftUiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "financial-draft.sqlite"
        initialize_database(self.db)
        created, _ = create_user("Compte test", "draft@example.invalid", "test-password-only-456", self.db)
        self.assertTrue(created)
        self.user = authenticate_user("draft@example.invalid", "test-password-only-456", self.db)
        for name, value in {
            "DATABASE_PATH": self.db,
            "is_authenticated": lambda: True,
            "current_user": lambda: self.user,
        }.items():
            active_patch = patch.object(property_analysis, name, value)
            active_patch.start()
            self.addCleanup(active_patch.stop)
        self.source = "import components.property_analysis as page\npage.show_property_analysis()\n"

    def tearDown(self):
        self.tmp.cleanup()

    def test_financial_inputs_resume_in_a_fresh_streamlit_session(self):
        app = AppTest.from_string(self.source, default_timeout=20).run()
        app.text_input(key="workflow_property_name").set_value("Dossier exemple").run()
        app.selectbox(key="workflow_property_type").set_value("Maison").run()
        app.radio(key="workflow_objective_choice").set_value("Investir et louer").run()
        app.number_input(key="iv_asking").set_value(425000.0).run()
        app.button(key="continue_to_finances").click().run()
        app.number_input(key="property_price").set_value(400000.0)
        app.number_input(key="down_payment").set_value(80000.0)
        app.number_input(key="mortgage_rate").set_value(5.0)
        app.date_input(key="mortgage_renewal_date").set_value(date(2028, 6, 1))
        app.run()
        self.assertFalse(app.exception)

        draft, step = load_draft(self.user["id"], self.db)
        self.assertGreaterEqual(step, 3)
        self.assertEqual(draft["financial_values"]["property_price"], 400000.0)
        self.assertEqual(draft["financial_values"]["down_payment"], 80000.0)
        self.assertEqual(draft["financial_values"]["mortgage_renewal_date"], "2028-06-01")

        resumed = AppTest.from_string(self.source, default_timeout=20).run()
        self.assertFalse(resumed.exception)
        self.assertEqual(resumed.number_input(key="property_price").value, 400000.0)
        self.assertEqual(resumed.number_input(key="down_payment").value, 80000.0)
        self.assertEqual(resumed.number_input(key="mortgage_rate").value, 5.0)
        self.assertEqual(resumed.date_input(key="mortgage_renewal_date").value, date(2028, 6, 1))
        self.assertEqual(resumed.session_state["analysis_property_name_value"], "Dossier exemple")
        self.assertEqual(resumed.session_state["analysis_property_type_value"], "Maison")
        self.assertEqual(resumed.session_state["workflow_objective"], "Investir et louer")
        self.assertEqual(resumed.session_state["iv_asking"], 425000.0)

    def test_drafts_are_owner_scoped_and_malformed_values_are_ignored(self):
        first = AppTest.from_string(self.source, default_timeout=20).run()
        first.text_input(key="workflow_property_name").set_value("Dossier exemple").run()
        first.selectbox(key="workflow_property_type").set_value("Maison").run()
        first.button(key="continue_to_finances").click().run()
        first.number_input(key="property_price").set_value(350000.0).run()
        other_created, _ = create_user("Autre compte", "other@example.invalid", "test-password-only-789", self.db)
        self.assertTrue(other_created)
        self.user = authenticate_user("other@example.invalid", "test-password-only-789", self.db)
        other = AppTest.from_string(self.source, default_timeout=20).run()
        self.assertEqual(load_draft(self.user["id"], self.db)[0].get("financial_values"), None)
        self.assertEqual(other.session_state["analysis_financial_values"]["property_price"], 0.0)

        save_draft(self.user["id"], {
            "financial_values": {
                "property_price": "not-a-number",
                "mortgage_rate": float("inf"),
                "amortization_years": 999,
                "mortgage_renewal_date": "invalid-date",
            }
        }, 3, self.db)
        malformed = AppTest.from_string(self.source, default_timeout=20).run()
        self.assertFalse(malformed.exception)
        self.assertEqual(malformed.number_input(key="property_price").value, 0.0)
        self.assertEqual(malformed.number_input(key="mortgage_rate").value, 0.0)
        self.assertEqual(malformed.date_input(key="mortgage_renewal_date").value, None)

    def test_reset_replaces_persisted_financial_values(self):
        app = AppTest.from_string(self.source, default_timeout=20).run()
        app.text_input(key="workflow_property_name").set_value("Dossier exemple").run()
        app.selectbox(key="workflow_property_type").set_value("Maison").run()
        app.button(key="continue_to_finances").click().run()
        app.number_input(key="property_price").set_value(300000.0).run()
        self.assertEqual(load_draft(self.user["id"], self.db)[0]["financial_values"]["property_price"], 300000.0)
        app.button(key="reset_analysis").click().run()
        self.assertEqual(load_draft(self.user["id"], self.db)[0]["financial_values"]["property_price"], 0.0)
        resumed = AppTest.from_string(self.source, default_timeout=20).run()
        self.assertEqual(resumed.number_input(key="property_price").value, 0.0)


if __name__ == "__main__":
    unittest.main()
