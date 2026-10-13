import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from data.database import create_user, get_user, initialize_database
from repositories.sqlite_repository import SQLiteRepository
from services.demo_service import demo_snapshot
from services.password_recovery_service import request_recovery
from streamlit.testing.v1 import AppTest


class LaunchUiJourneys(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "journey.sqlite"
        initialize_database(self.db)
        create_user("Client", "ui-client@example.test", "old-long-password", self.db)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE users SET plan='premium' WHERE id=1")
        snapshot, _ = demo_snapshot()
        self.analysis_id = SQLiteRepository(self.db).save_analysis(1, "Duplex du client", snapshot)

    def tearDown(self):
        self.temp.cleanup()

    def test_premium_can_save_criteria_and_get_screening(self):
        source = f'''
from pathlib import Path
from components.investment_criteria import show_investment_criteria
from data.database import get_user, list_analyses
db = Path({str(self.db)!r})
show_investment_criteria(get_user(1, db), list_analyses(1, db), db)
'''
        app = AppTest.from_string(source).run(timeout=20)
        self.assertFalse(app.exception)
        app.checkbox(key="criterion_enabled_1_min_cash_flow").set_value(True)
        app.number_input(key="criterion_value_1_min_cash_flow").set_value(300)
        next(button for button in app.button if button.label == "Enregistrer mes critères").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Critères enregistrés" in item.value for item in app.success))
        self.assertTrue(app.dataframe)
        self.assertIn("Correspond à vos critères", app.dataframe[0].value.to_string())

    def test_recovery_form_updates_password_and_clears_token_from_url(self):
        sender = Mock()
        env = {"IMMORADAR_AUTH_EMAIL_ENABLED": "1", "IMMORADAR_PUBLIC_URL": "https://example.test",
               "BREVO_API_KEY": "placeholder", "BREVO_SENDER_EMAIL": "sender@example.test"}
        request_recovery("ui-client@example.test", self.db, env, sender)
        token = re.search(r"reset_token=([A-Za-z0-9_-]+)", sender.call_args.args[2]).group(1)
        app = AppTest.from_string(f'''
from components.password_recovery import show_recovery
show_recovery({str(self.db)!r})
''')
        app.query_params["reset_token"] = token
        app.run(timeout=20)
        app.text_input(key="recovery_new_password").set_value("new-long-password")
        app.text_input(key="recovery_confirmation").set_value("new-long-password")
        next(button for button in app.button if button.label == "Enregistrer mon nouveau mot de passe").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertNotIn("reset_token", app.query_params)
        self.assertTrue(any("mot de passe a été modifié" in item.value for item in app.success))

    def test_revoked_session_is_signed_out_on_next_read(self):
        source = f'''
import streamlit as st
from unittest.mock import patch
import components.account as account
from data.database import get_user
with patch.object(account, "get_user", lambda identifier: get_user(identifier, {str(self.db)!r})):
    if account._active_user() is None:
        st.write("SESSION FERMÉE")
    else:
        st.write("SESSION ACTIVE")
'''
        app = AppTest.from_string(source)
        app.session_state["current_user"] = get_user(1, self.db)
        app.run(timeout=20)
        self.assertIn("SESSION ACTIVE", " ".join(item.value for item in app.markdown))
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE users SET session_version=session_version+1 WHERE id=1")
        app.run(timeout=20)
        self.assertIn("SESSION FERMÉE", " ".join(item.value for item in app.markdown))
        self.assertFalse(app.exception)
