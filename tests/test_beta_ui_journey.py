"""Exercise account creation and the visual onboarding against isolated SQLite."""

import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data.database import initialize_database
from repositories.sqlite_repository import SQLiteRepository
from services.beta_service import create_invitation, register_beta_user, validate_invitation


class BetaUiJourneyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database_path = Path(self.temporary.name) / "beta-ui.sqlite"
        initialize_database(self.database_path)
        created, _ = register_beta_user(
            "Compte de test", "founder@example.invalid", "test-password-only-123",
            self.database_path, development_mode=True,
        )
        self.assertTrue(created)
        with closing(SQLiteRepository(self.database_path)._connect()) as connection, connection:
            connection.execute("UPDATE users SET role='admin' WHERE id=1")
            connection.execute(
                "UPDATE beta_settings SET registrations_open=1, invitation_required=1, max_participants=10"
            )
        self.invitation = create_invitation(1, self.database_path, "interface", 1)

    def _app(self):
        # Patch only this AppTest script. The real database is never opened by
        # account/session lookups, including after each Streamlit rerun.
        source = f'''
from pathlib import Path
import components.account as page
from data.database import authenticate_user, get_user, count_analyses
database_path = Path({str(self.database_path)!r})
original_database_path = page.DATABASE_PATH
original_is_authenticated = page.is_authenticated
original_current_user = page.current_user
original_authenticate = page.authenticate_user
original_get_user = page.get_user
original_count = page.count_analyses
try:
    page.DATABASE_PATH = database_path
    page.is_authenticated = lambda: page._active_user() is not None
    page.current_user = lambda: page._active_user()
    page.authenticate_user = lambda email, password: authenticate_user(email, password, database_path)
    page.get_user = lambda user_id: get_user(user_id, database_path)
    page.count_analyses = lambda user_id: count_analyses(user_id, database_path)
    page.show_account()
finally:
    page.DATABASE_PATH = original_database_path
    page.is_authenticated = original_is_authenticated
    page.current_user = original_current_user
    page.authenticate_user = original_authenticate
    page.get_user = original_get_user
    page.count_analyses = original_count
'''
        return AppTest.from_string(source, default_timeout=20)

    def _user(self):
        return SQLiteRepository(self.database_path).get_user_by_email("visitor@example.invalid")

    def _click(self, app, label):
        button = next(item for item in app.button if item.label == label)
        button.click().run()
        self.assertFalse(app.exception)

    def test_registration_interruption_resume_and_completion_in_the_ui(self):
        app = self._app().run()
        self.assertFalse(app.exception)
        app.text_input[2].set_value("Visiteur de test")
        app.text_input(key="register_email").set_value("visitor@example.invalid")
        app.text_input(key="register_password").set_value("test-password-only-456")
        app.text_input[5].set_value("test-password-only-456")
        app.text_input[6].set_value(self.invitation)
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(validate_invitation(self.invitation, self.database_path), "exhausted")
        self.assertIsNotNone(self._user())
        self.assertEqual(self._user()["onboarding_step"], 1)
        self.assertEqual(self._user()["onboarding_completed"], 0)
        self._click(app, "Suivant")
        self.assertEqual(self._user()["onboarding_step"], 2)
        app.selectbox[0].set_value("Premier acheteur").run()
        self._click(app, "Suivant")
        self.assertEqual(self._user()["user_type"], "Premier acheteur")
        app.selectbox[0].set_value("Acheter pour y habiter").run()
        self._click(app, "Suivant")
        self.assertEqual(self._user()["onboarding_step"], 4)
        self.assertEqual(self._user()["user_objective"], "Acheter pour y habiter")

        # Leaving this screen and constructing another AppTest simulates an
        # interrupted browser session, not merely one extra script rerun.
        self._click(app, "Reprendre plus tard")
        resumed = self._app()
        resumed.session_state["current_user"] = self._user()
        app = resumed.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox[0].label, "Horizon (facultatif)")
        for expected_step in range(5, 10):
            self._click(app, "Suivant")
            self.assertEqual(self._user()["onboarding_step"], expected_step)
        self.assertEqual(self._user()["onboarding_completed"], 0)
        self._click(app, "Terminer")
        self.assertEqual(self._user()["onboarding_completed"], 0)
        self.assertTrue(any("requis" in item.value for item in app.error))
        app.checkbox[0].set_value(True).run()
        self._click(app, "Terminer")
        self.assertEqual(self._user()["onboarding_completed"], 1)
        self.assertIsNotNone(self._user()["onboarding_completed_at"])
        completed = self._app()
        completed.session_state["current_user"] = self._user()
        completed.run()
        self.assertFalse(completed.exception)
        self.assertIn("Se déconnecter", [item.label for item in completed.button])
        self.assertNotIn("Suivant", [item.label for item in completed.button])
        self._click(completed, "Analyser une propriété")
        self.assertEqual(completed.session_state["main_navigation"], "Analyser")

    def test_invalid_invitation_is_rejected_before_creating_an_account(self):
        app = self._app().run()
        app.text_input[2].set_value("Autre visiteur")
        app.text_input(key="register_email").set_value("visitor@example.invalid")
        app.text_input(key="register_password").set_value("test-password-only-456")
        app.text_input[5].set_value("test-password-only-456")
        app.text_input[6].set_value("invalid-test-code")
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Code d'invitation invalide" in item.value for item in app.error))
        self.assertIsNone(self._user())
        self.assertEqual(validate_invitation(self.invitation, self.database_path), "active")

    def test_guest_analysis_requires_an_explicit_calculation(self):
        source = f'''
from pathlib import Path
import components.property_analysis as page
original_database_path = page.DATABASE_PATH
original_is_authenticated = page.is_authenticated
try:
    page.DATABASE_PATH = Path({str(self.database_path)!r})
    page.is_authenticated = lambda: False
    page.show_property_analysis()
finally:
    page.DATABASE_PATH = original_database_path
    page.is_authenticated = original_is_authenticated
'''
        app = AppTest.from_string(source, default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertIn("Continuer vers les finances", [item.label for item in app.button])
        self.assertNotIn("ImmoScore", [item.label for item in app.metric])
        app.text_input(key="workflow_property_name").set_value("Projet de test")
        app.selectbox(key="workflow_property_type").set_value("Maison")
        self._click(app, "Continuer vers les finances")
        self.assertIn("Calculer mon analyse", [item.label for item in app.button])
        self.assertNotIn("ImmoScore", [item.label for item in app.metric])
        app.number_input(key="property_price").set_value(400000.0)
        app.number_input(key="down_payment").set_value(80000.0)
        app.number_input(key="mortgage_rate").set_value(5.0)
        app.run()
        self._click(app, "Calculer mon analyse")
        self.assertIn("ImmoScore", [item.label for item in app.metric])
        self.assertIn("Créer mon espace gratuit", [item.label for item in app.button])

    def test_signed_in_analysis_is_saved_and_visible_in_my_properties(self):
        created, _ = register_beta_user(
            "Visiteur de test", "visitor@example.invalid", "test-password-only-456",
            self.database_path, invitation_code=self.invitation,
        )
        self.assertTrue(created)
        source = f'''
from pathlib import Path
import streamlit as st
import components.property_analysis as analysis_page
import components.saved_analyses as saved_page
from data.database import authenticate_user, save_analysis, list_analyses
database_path = Path({str(self.database_path)!r})
user = authenticate_user("visitor@example.invalid", "test-password-only-456", database_path)
originals = {{
    "analysis_db": analysis_page.DATABASE_PATH,
    "analysis_auth": analysis_page.is_authenticated,
    "analysis_user": analysis_page.current_user,
    "analysis_save": analysis_page.save_analysis,
    "saved_db": saved_page.DATABASE_PATH,
    "saved_auth": saved_page.is_authenticated,
    "saved_user": saved_page.current_user,
    "saved_list": saved_page.list_analyses,
    "saved_alerts": saved_page.show_alert_center,
}}
try:
    analysis_page.DATABASE_PATH = database_path
    analysis_page.is_authenticated = lambda: True
    analysis_page.current_user = lambda: user
    analysis_page.save_analysis = lambda owner, name, values, **kwargs: save_analysis(
        owner, name, values, database_path, **kwargs
    )
    saved_page.DATABASE_PATH = database_path
    saved_page.is_authenticated = lambda: True
    saved_page.current_user = lambda: user
    saved_page.list_analyses = lambda owner, _path=database_path: list_analyses(owner, database_path)
    saved_page.show_alert_center = lambda *_args, **_kwargs: None
    if st.session_state.get("main_navigation") == "Mes propriétés":
        saved_page.show_saved_analyses()
    else:
        analysis_page.show_property_analysis()
finally:
    analysis_page.DATABASE_PATH = originals["analysis_db"]
    analysis_page.is_authenticated = originals["analysis_auth"]
    analysis_page.current_user = originals["analysis_user"]
    analysis_page.save_analysis = originals["analysis_save"]
    saved_page.DATABASE_PATH = originals["saved_db"]
    saved_page.is_authenticated = originals["saved_auth"]
    saved_page.current_user = originals["saved_user"]
    saved_page.list_analyses = originals["saved_list"]
    saved_page.show_alert_center = originals["saved_alerts"]
'''
        app = AppTest.from_string(source, default_timeout=20).run()
        self.assertFalse(app.exception)
        app.text_input(key="workflow_property_name").set_value("Projet de test")
        app.selectbox(key="workflow_property_type").set_value("Maison")
        self._click(app, "Continuer vers les finances")
        app.selectbox(key="analysis_step_selector").set_value(1).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key="workflow_property_name").value, "Projet de test")
        self.assertEqual(app.selectbox(key="workflow_property_type").value, "Maison")
        self._click(app, "Continuer vers les finances")
        app.number_input(key="property_price").set_value(400000.0)
        app.number_input(key="down_payment").set_value(80000.0)
        app.number_input(key="mortgage_rate").set_value(5.0)
        app.run()
        self._click(app, "Calculer mon analyse")
        self.assertIn("Sauvegarder mon dossier", [item.label for item in app.button])
        self._click(app, "Sauvegarder mon dossier")
        self.assertTrue(
            any("sauvegardés" in item.value for item in app.success),
            (
                [item.value for item in app.error],
                [item.value for item in app.success],
                app.session_state["workflow_property_name"] if "workflow_property_name" in app.session_state else None,
                app.session_state["saved_property_name"] if "saved_property_name" in app.session_state else None,
            ),
        )
        owner_id = self._user()["id"]
        analyses = SQLiteRepository(self.database_path).list_analyses(owner_id)
        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0]["property_name"], "Projet de test")
        self.assertEqual(json.loads(analyses[0]["financial_inputs_json"])["_property_type"], "Maison")
        self.assertEqual(SQLiteRepository(self.database_path).list_analyses(1), [])
        app.session_state["main_navigation"] = "Mes propriétés"
        app.run()
        self.assertFalse(app.exception)
        self.assertIn("Projet de test", " ".join(item.label for item in app.expander))


if __name__ == "__main__":
    unittest.main()
