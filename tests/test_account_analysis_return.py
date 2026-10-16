"""Regression tests for the guest-analysis to local-account conversion path."""

import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest
from data.database import create_user, get_user, initialize_database
from services.onboarding_service import complete, progress


class AccountAnalysisReturnTests(unittest.TestCase):
    def _premium_return_app(self, database_path):
        return AppTest.from_string(f'''
from pathlib import Path
from unittest.mock import patch
import streamlit as st
import components.account as page
from data.database import authenticate_user, get_user
db = Path({str(database_path)!r})
with patch.multiple(page, DATABASE_PATH=db,
    authenticate_user=lambda email, password: authenticate_user(email, password, db),
    get_user=lambda user_id: get_user(user_id, db)):
    if st.session_state.get("main_navigation") == "Premium":
        st.write("OFFRE PREMIUM RETROUVÉE")
    else:
        page.show_account()
''', default_timeout=20)

    def test_existing_customer_resumes_premium_only_after_valid_login(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "premium-return.sqlite"
            initialize_database(db)
            create_user("Client", "client@example.test", "password-test-123", db)
            progress(1, db, user_type="Propriétaire", user_objective="Acheter", limitations_accepted=1)
            self.assertTrue(complete(1, db))
            app = self._premium_return_app(db)
            app.session_state["return_to_premium_after_auth"] = True
            app.run()
            app.text_input(key="login_email").set_value("client@example.test")
            app.text_input(key="login_password").set_value("wrong-password-123")
            app.button(key="FormSubmitter:login_form-Se connecter").click().run()
            self.assertTrue(app.error)
            self.assertTrue(app.session_state["return_to_premium_after_auth"])
            self.assertNotIn("current_user", app.session_state)
            app.text_input(key="login_password").set_value("password-test-123")
            app.button(key="FormSubmitter:login_form-Se connecter").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["main_navigation"], "Premium")
            self.assertNotIn("return_to_premium_after_auth", app.session_state)
            self.assertEqual(get_user(1, db)["plan"], "free")
            self.assertNotIn("billing_checkout_url", app.session_state)

    def test_new_customer_resumes_premium_after_required_onboarding(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "premium-new-account.sqlite"
            initialize_database(db)
            create_user("Client", "client@example.test", "password-test-123", db)
            progress(1, db, onboarding_step=9, user_type="Propriétaire", user_objective="Acheter")
            app = self._premium_return_app(db)
            app.session_state["current_user"] = get_user(1, db)
            app.session_state["return_to_premium_after_auth"] = True
            app.run()
            next(button for button in app.button if button.label == "Terminer").click().run()
            self.assertTrue(app.error)
            self.assertTrue(app.session_state["return_to_premium_after_auth"])
            self.assertFalse(get_user(1, db)["onboarding_completed"])
            app.checkbox[0].set_value(True)
            next(button for button in app.button if button.label == "Terminer").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(get_user(1, db)["onboarding_completed"])
            self.assertEqual(app.session_state["main_navigation"], "Premium")
            self.assertNotIn("return_to_premium_after_auth", app.session_state)
            self.assertEqual(get_user(1, db)["plan"], "free")
            self.assertNotIn("billing_checkout_url", app.session_state)

    def test_registration_defers_preferences_to_the_visual_onboarding(self):
        source = (Path("components") / "account.py").read_text(encoding="utf-8")
        self.assertIn("Vous choisirez votre profil et vos préférences", source)
        self.assertNotIn('selectbox("Type d\'utilisateur"', source)

    def test_analysis_cta_keeps_only_a_safe_return_destination(self):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            "st.session_state['return_to_premium_after_auth'] = True\n"
            "page._open_account_to_keep_analysis()\n"
            "st.write(st.session_state.get('main_navigation'))\n"
        ).run(timeout=20)
        self.assertEqual(app.session_state["main_navigation"], "Mon compte")
        self.assertTrue(app.session_state["return_to_analysis_after_auth"])
        self.assertNotIn("return_to_premium_after_auth", app.session_state)

    def test_completed_account_returns_to_the_analysis_draft(self):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "import components.account as page\n"
            "st.session_state[page.RETURN_TO_ANALYSIS_KEY] = True\n"
            "st.write(page._resume_analysis_after_authentication())\n"
        ).run(timeout=20)
        self.assertEqual(app.session_state["main_navigation"], "Analyser")
        self.assertNotIn("return_to_analysis_after_auth", app.session_state)

    def test_new_account_starts_a_local_session_and_onboarding(self):
        with tempfile.TemporaryDirectory() as temp:
            database_path = Path(temp) / "account-return.sqlite"
            source = f'''
from pathlib import Path
import streamlit as st
import components.account as page
from data.database import initialize_database, create_user as persist_user, authenticate_user as authenticate
initialize_database(Path({str(database_path)!r}))
page.DATABASE_PATH = Path({str(database_path)!r})
page.authenticate_user = lambda email, password: authenticate(email, password, Path({str(database_path)!r}))
persist_user("Nouveau compte", "nouveau-compte@example.test", "Motdepasse123", Path({str(database_path)!r}))
page._start_new_account_session("nouveau-compte@example.test", "Motdepasse123")
st.write(st.session_state.get("current_user"))
'''
            app = AppTest.from_string(source).run(timeout=20)
            self.assertIn("current_user", app.session_state)
            self.assertEqual(app.session_state["current_user"]["user_type"], "")


if __name__ == "__main__":
    unittest.main()
