"""Real Streamlit form regressions for canonical address-state synchronization."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data.database import create_user, initialize_database
from services.address_form_service import restore_address_form, serialize_address_form, submit_address_form
from services.analysis_workflow import load_draft, save_draft
from services.quebec_role_admin_service import import_territory, refresh_index


INDEX = (
    "code géographique,nom du territoire,lien,date de modification\n"
    "70022,Beauharnois,https://mamh.gouv.qc.ca/role/RM70022.xml,2025-12-19\n"
).encode()
XML = (
    b'\xef\xbb\xbf<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>70022</RLM01A>'
    b'<RLM02A>2026</RLM02A><RLUEx><RL0101><RL0101Ax>262</RL0101Ax>'
    b'<RL0101Gx>EDGAR-H\xc3\x89BERT</RL0101Gx></RL0101><RL0104><RL0104A>1</RL0104A>'
    b'</RL0104><RL0402A>125400</RL0402A><RL0403A>278700</RL0403A><RL0404A>404100</RL0404A>'
    b'<RL0401A>2024-07-01</RL0401A></RLUEx></RL>'
)


class AddressFormUiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "address-ui.sqlite"
        initialize_database(self.db)
        create_user("Admin", "admin@example.com", "Motdepasse1", self.db)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE users SET role='admin' WHERE email='admin@example.com'")
        refresh_index(1, self.db, lambda _: INDEX)
        import_territory(1, self.db, "70022", lambda _: XML)
        self.app_source = (
            "from pathlib import Path\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "page.show_property_analysis()\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _app(self, authenticated=False):
        source = self.app_source
        if authenticated:
            source = (
                "import streamlit as st\n"
                "import components.account as account\n"
                "account.get_user = lambda user_id: {'id': user_id, 'user_type': 'Investisseur locatif', 'plan': 'free'}\n"
                "st.session_state.setdefault('current_user', {'id': 1})\n"
                + source
            )
        app = AppTest.from_string(source)
        app.run(timeout=20)
        return app

    @staticmethod
    def _submit_exact(app):
        app.text_input(key="address_form_street").set_value("262 Rue Edgar-Hébert, Beauharnois, QC, Canada")
        app.text_input(key="address_form_city").set_value("Beauharnois")
        app.text_input(key="address_form_postal").set_value("J6N0A4")
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)

    def test_exact_submission_visible_values_and_two_reruns_are_consistent(self):
        app = self._app()
        self.assertEqual(list(app.error), [])
        self._submit_exact(app)
        self.assertEqual(app.text_input(key="address_form_city").value, "Beauharnois")
        self.assertEqual(app.text_input(key="address_form_postal").value, "J6N 0A4")
        self.assertTrue(app.checkbox(key="address_form_consent").value)
        self.assertEqual(list(app.error), [])

    def test_street_only_submission_keeps_city_postal_and_consent_canonical(self):
        app = self._app()
        app.text_input(key="address_form_street").set_value("262 Rue Edgar-Hébert")
        app.text_input(key="address_form_city").set_value("Beauharnois")
        app.text_input(key="address_form_postal").set_value("J6N 0A4")
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_street").value, "262 Rue Edgar-Hébert")
        self.assertEqual(app.text_input(key="address_form_city").value, "Beauharnois")
        self.assertEqual(app.text_input(key="address_form_postal").value, "J6N 0A4")
        self.assertTrue(app.checkbox(key="address_form_consent").value)
        self.assertEqual(list(app.error), [])
        self.assertTrue(any("Beauharnois (territoire 70022)" in item.value for item in app.success))
        self.assertTrue(any("404 100 $" in item.value for item in app.info))
        app.run(timeout=20)
        app.run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Beauharnois")
        self.assertEqual(app.text_input(key="address_form_postal").value, "J6N 0A4")
        self.assertEqual(list(app.error), [])

    def test_error_is_cleared_only_by_a_valid_new_submission(self):
        app = self._app()
        app.text_input(key="address_form_street").set_value("262 Rue Edgar-Hébert")
        app.text_input(key="address_form_city").set_value("")
        app.text_input(key="address_form_postal").set_value("J6N0A4")
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertTrue(any("Ce champ est requis." in item.value for item in app.error))
        app.text_input(key="address_form_city").set_value("Beauharnois")
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertEqual(list(app.error), [])
        self.assertEqual(app.text_input(key="address_form_city").value, "Beauharnois")

    def test_drafts_restore_the_same_canonical_values_without_cross_user_leakage(self):
        first = submit_address_form("262 Rue Edgar-Hébert, Beauharnois, QC, Canada", "Beauharnois", "J6N0A4", consent=True)
        second = submit_address_form("12 rue du Port", "Montréal", "H2X1Y4", consent=False)
        self.assertTrue(first.valid); self.assertTrue(second.valid)
        create_user("Deux", "deux@example.com", "Motdepasse1", self.db)
        save_draft(1, {"address_form": serialize_address_form(first)}, 2, self.db)
        save_draft(2, {"address_form": serialize_address_form(second)}, 2, self.db)
        first_payload, _ = load_draft(1, self.db)
        second_payload, _ = load_draft(2, self.db)
        first_restored = restore_address_form(first_payload["address_form"])
        second_restored = restore_address_form(second_payload["address_form"])
        self.assertEqual(first_restored.values["postal"], "J6N 0A4")
        self.assertEqual(first_restored.values["city"], "Beauharnois")
        self.assertNotEqual(first_restored.values["street"], second_restored.values["street"])
        self.assertFalse(second_restored.values["consent"])

    def test_authenticated_draft_resumes_in_the_real_form(self):
        state = submit_address_form("262 Rue Edgar-Hébert, Beauharnois, QC, Canada", "Beauharnois", "J6N0A4", consent=True)
        save_draft(1, {"address_form": serialize_address_form(state)}, 2, self.db)
        app = self._app(authenticated=True)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.text_input(key="address_form_street").value, "262 Rue Edgar-Hébert, Beauharnois, QC, Canada")
        self.assertEqual(app.text_input(key="address_form_city").value, "Beauharnois")
        self.assertEqual(app.text_input(key="address_form_postal").value, "J6N 0A4")
        self.assertTrue(app.checkbox(key="address_form_consent").value)
        app.run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Beauharnois")
