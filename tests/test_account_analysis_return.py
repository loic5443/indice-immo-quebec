"""Regression tests for the guest-analysis to local-account conversion path."""

import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AccountAnalysisReturnTests(unittest.TestCase):
    def test_analysis_cta_keeps_only_a_safe_return_destination(self):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            "page._open_account_to_keep_analysis()\n"
            "st.write(st.session_state.get('main_navigation'))\n"
        ).run(timeout=20)
        self.assertEqual(app.session_state["main_navigation"], "Mon compte")
        self.assertTrue(app.session_state["return_to_analysis_after_auth"])

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
import components.account as page
from data.database import initialize_database, create_user as persist_user, authenticate_user as authenticate, get_user as persisted_user
initialize_database(Path({str(database_path)!r}))
page.DATABASE_PATH = Path({str(database_path)!r})
page.create_user = lambda name, email, password, profile=None: persist_user(name, email, password, Path({str(database_path)!r}), profile)
page.authenticate_user = lambda email, password: authenticate(email, password, Path({str(database_path)!r}))
page.get_user = lambda user_id: persisted_user(user_id, Path({str(database_path)!r}))
page.registration_allowed = lambda code, database: (True, "")
page.show_account()
'''
            app = AppTest.from_string(source).run(timeout=20)
            self.assertEqual(len(app.selectbox), 0)
            self.assertTrue(any("profil et vos préférences" in item.value for item in app.caption))
            app.text_input[2].set_value("Nouveau compte").run(timeout=20)
            app.text_input(key="register_email").set_value("nouveau-compte@example.test").run(timeout=20)
            app.text_input(key="register_password").set_value("Motdepasse123").run(timeout=20)
            app.text_input[5].set_value("Motdepasse123").run(timeout=20)
            app.button[1].click().run(timeout=20)
            self.assertFalse(app.error, [item.value for item in app.error])
            self.assertIn("current_user", app.session_state)
            self.assertEqual(app.session_state["current_user"]["user_type"], "")
            self.assertTrue(any("Bienvenue dans ImmoRadar" in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
