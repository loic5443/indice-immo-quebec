from contextlib import closing
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from data.database import create_user, get_user, initialize_database
from services.alert_delivery_service import _eligible_user
from services.alert_email_service import send_test_alert_email
from services.property_comparison_service import _snapshot
from streamlit.testing.v1 import AppTest


EMAIL_ENV = {"IMMORADAR_ALERT_DELIVERY_ENABLED": "true", "BREVO_API_KEY": "placeholder", "BREVO_SENDER_EMAIL": "sender@example.test"}


class CommercialRightsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "commercial.sqlite"
        initialize_database(self.db)
        create_user("Client", "paid@example.test", "long-password-test", self.db)
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE users SET alert_email_consent=1 WHERE id=1")
            connection.execute("INSERT INTO billing_accounts(user_id,customer_id,subscription_id,status,access_until) VALUES(1,'cus_fixture','sub_fixture','active',?)", (int(time.time())+86400,))
        self.sender = Mock()

    def tearDown(self):
        self.temp.cleanup()

    def test_paid_account_receives_alert_rights_even_if_legacy_plan_is_free(self):
        self.assertEqual(_eligible_user(1, self.db)["plan"], "premium")
        self.assertEqual(send_test_alert_email(1, self.db, environment=EMAIL_ENV, sender=self.sender), "sent")
        self.sender.assert_called_once()
        with closing(sqlite3.connect(self.db)) as connection, connection:
            self.assertEqual(connection.execute("SELECT plan FROM users WHERE id=1").fetchone()[0], "free")

    def test_canceled_paid_account_cannot_use_stale_beta_premium(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE users SET plan='premium' WHERE id=1")
            connection.execute("UPDATE billing_accounts SET status='canceled' WHERE user_id=1")
        self.assertIsNone(_eligible_user(1, self.db))
        self.assertEqual(send_test_alert_email(1, self.db, environment=EMAIL_ENV, sender=self.sender), "not_entitled")
        self.sender.assert_not_called()

    def test_expired_paid_period_stops_alert_delivery(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE billing_accounts SET access_until=1 WHERE user_id=1")
        self.assertIsNone(_eligible_user(1, self.db))
        self.assertEqual(send_test_alert_email(1, self.db, environment=EMAIL_ENV, sender=self.sender), "not_entitled")
        self.sender.assert_not_called()


class SnapshotIntegrityTests(unittest.TestCase):
    def test_zero_scenario_value_is_not_replaced_by_another_value(self):
        row = {"id": 1, "cash_flow": 500, "scenarios_json": json.dumps([{"name": "Scénario de base", "financial": {"cash_flow_monthly": 0, "monthly_payment": 0}}]),
               "financial_inputs_json": json.dumps({"monthly_payment": 2000})}
        snapshot = _snapshot(row)
        self.assertEqual(snapshot["base_cash_flow"], 0)
        self.assertEqual(snapshot["monthly_payment"], 0)

    def test_invalid_numbers_do_not_get_an_investment_comparison(self):
        row = {"id": 1, "price": float("nan"), "cash_flow": True, "immo_score": float("inf")}
        snapshot = _snapshot(row)
        for key in ("price", "cash_flow", "score"):
            self.assertIsNone(snapshot[key])

    def test_logout_clears_private_analysis_and_payment_session_state(self):
        app = AppTest.from_string('''
import streamlit as st
from components.account import logout
st.button("Sortir", on_click=logout)
''')
        app.session_state["current_user"] = {"id": 1}
        app.session_state["iv_manual_comparables"] = [{"address": "Private test"}]
        app.session_state["billing_checkout_url"] = "https://checkout.stripe.com/test"
        app.session_state["financial_secret_fixture"] = 500000
        app.run(timeout=20)
        app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        for key in ("current_user", "iv_manual_comparables", "billing_checkout_url", "financial_secret_fixture"):
            self.assertNotIn(key, app.session_state)
        self.assertEqual(app.session_state["main_navigation"], "Accueil")


class SavedScenarioJourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "saved.sqlite"
        initialize_database(self.db)
        create_user("Client", "scenario@example.test", "long-password-test", self.db)

    def tearDown(self):
        self.temp.cleanup()

    def app(self, interest=5):
        return AppTest.from_string(f'''
from pathlib import Path
from unittest.mock import patch
import components.property_analysis as page
from data.database import get_user, save_analysis
from calculations.real_estate import calculate_analysis
from services.demo_service import demo_inputs
db = Path({str(self.db)!r})
inputs = demo_inputs(interest={interest})
with patch.object(page,"DATABASE_PATH",db), patch.object(page,"is_authenticated",lambda:True), patch.object(page,"current_user",lambda:get_user(1,db)), patch.object(page,"save_analysis",lambda owner,name,values,profile,engine_result:save_analysis(owner,name,values,db,profile,engine_result)):
    page._apply_reopen_draft()
    page._show_results(inputs,calculate_analysis(inputs),"Investisseur locatif")
''').run(timeout=20)

    def saved(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("SELECT * FROM analyses ORDER BY id")]

    def test_actual_save_keeps_scenarios_and_resilience_and_custom_change(self):
        app = self.app()
        app.text_input(key="saved_property_name").set_value("Dossier de test").run(timeout=20)
        app.button(key="save_analysis").click().run(timeout=20)
        self.assertFalse(app.exception)
        first = self.saved()[0]
        self.assertEqual(len(json.loads(first["scenarios_json"])), 3)
        self.assertEqual(len(json.loads(first["resilience_json"])["tests"]), 5)
        next(field for field in app.checkbox if field.label == "Inclure ce scénario").set_value(True).run(timeout=20)
        next(field for field in app.number_input if field.label == "Taux personnalisé (%)").set_value(6.0).run(timeout=20)
        app.button(key="save_analysis").click().run(timeout=20)
        self.assertFalse(app.exception)
        saved = self.saved()
        self.assertEqual(len(saved), 2)
        custom = next(row for row in json.loads(saved[1]["scenarios_json"]) if row["name"] == "Personnalisé")
        self.assertEqual(custom["inputs"]["annual_interest_rate"], 6)
        app.button(key="save_analysis").click().run(timeout=20)
        self.assertEqual(len(self.saved()), 2)

    def test_reopening_keeps_custom_scenario_without_touching_saved_values(self):
        from services.analysis_reopen_service import prepare_reopen_draft
        app = self.app()
        app.text_input(key="saved_property_name").set_value("Dossier personnalisé").run(timeout=20)
        app.checkbox(key="scenario_custom_include").set_value(True)
        app.number_input(key="scenario_custom_rate").set_value(6.0)
        app.number_input(key="scenario_custom_expenses").set_value(1.2)
        app.button(key="save_analysis").click().run(timeout=20)
        before = self.saved()[0]
        app.session_state["analysis_reopen_pending"] = prepare_reopen_draft(1, before["id"], self.db)
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(app.checkbox(key="scenario_custom_include").value)
        self.assertEqual(app.number_input(key="scenario_custom_rate").value, 6.0)
        self.assertAlmostEqual(app.number_input(key="scenario_custom_expenses").value, 1.2)
        self.assertEqual(self.saved()[0], before)

    def test_extreme_valid_rate_keeps_base_analysis_without_crash(self):
        app = self.app(interest=25)
        self.assertFalse(app.exception)
        self.assertTrue(any("limites" in item.value for item in app.info))
        self.assertTrue(app.metric)


class FreshDraftJourneyTests(unittest.TestCase):
    def test_new_dossier_keeps_account_and_saved_records_but_discards_old_draft(self):
        from services.analysis_workflow import save_draft, load_draft
        from repositories.sqlite_repository import SQLiteRepository
        from services.demo_service import demo_snapshot
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "new-draft.sqlite"
            initialize_database(db)
            create_user("Client", "new-draft@example.test", "long-password-test", db)
            create_user("Autre", "other-draft@example.test", "long-password-test", db)
            save_draft(1, {"property_details": {"property_name": "Ancien brouillon"}}, 3, db)
            save_draft(2, {"private_fixture": "Autre compte"}, 4, db)
            snapshot, _ = __import__("services.demo_service", fromlist=["demo_snapshot"]).demo_snapshot()
            SQLiteRepository(db).save_analysis(1, "Dossier conservé", snapshot)
            app = AppTest.from_string(f'''
import streamlit as st
from unittest.mock import patch
import components.property_analysis as page
from data.database import get_user
with patch.object(page,"DATABASE_PATH",{str(db)!r}), patch.object(page,"is_authenticated",lambda:True), patch.object(page,"current_user",lambda:get_user(1,{str(db)!r})):
    if st.session_state.get("main_navigation")=="Analyser":
        page.show_property_analysis()
    else:
        st.button("Nouveau dossier",on_click=page.start_new_analysis)
''')
            app.session_state["current_user"] = get_user(1, db)
            app.session_state["iv_manual_comparables"] = [{"address": "Comparables du précédent"}]
            app.session_state["workflow_property_name"] = "Ancien brouillon"
            app.run(timeout=20)
            app.button[0].click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["current_user"]["id"], 1)
            self.assertNotIn("iv_manual_comparables", app.session_state)
            fresh_draft, fresh_step = load_draft(1, db)
            self.assertEqual(fresh_step, 1)
            self.assertEqual(fresh_draft.get("property_details", {}).get("name", ""), "")
            self.assertNotIn("Ancien brouillon", str(fresh_draft))
            self.assertEqual(load_draft(2, db)[0], {"private_fixture": "Autre compte"})
            self.assertEqual(len(SQLiteRepository(db).list_analyses(1)), 1)
            self.assertEqual(app.session_state["analysis_step"], 1)


class NonRentalScenarioTests(unittest.TestCase):
    def test_owner_scenario_and_report_show_costs_without_a_rental_failure(self):
        from io import BytesIO
        from pypdf import PdfReader
        from services.demo_service import demo_inputs, demo_snapshot
        from services.report_service import generate_report_pdf
        from domain.scenarios import build_resilience_tests
        inputs = demo_inputs(rental_income=0)
        tests, status = build_resilience_tests(inputs, "Propriétaire")
        self.assertEqual(status, "non applicable sans revenu locatif")
        snapshot, _ = demo_snapshot(inputs)
        text = " ".join(page.extract_text() for page in PdfReader(BytesIO(generate_report_pdf(snapshot))).pages)
        self.assertIn("Coût mensuel", text)
        self.assertIn("résistance locative", text)
        self.assertIn("Non applicable sans revenu locatif", text)
