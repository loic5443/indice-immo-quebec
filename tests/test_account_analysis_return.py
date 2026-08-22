"""Regression tests for the guest-analysis to local-account conversion path."""

import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AccountAnalysisReturnTests(unittest.TestCase):
    def test_registration_defers_preferences_to_the_visual_onboarding(self):
        source = (Path("components") / "account.py").read_text(encoding="utf-8")
        self.assertIn("Vous choisirez votre profil et vos préférences", source)
        self.assertNotIn('selectbox("Type d\'utilisateur"', source)

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
