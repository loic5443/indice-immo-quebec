"""Exercise account creation and the visual onboarding against isolated SQLite."""

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


if __name__ == "__main__":
    unittest.main()
