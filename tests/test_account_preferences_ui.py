"""Focused UI checks for account preferences used by future dossiers only."""

import unittest

from streamlit.testing.v1 import AppTest


class AccountPreferencesUiTests(unittest.TestCase):
    def _app(self):
        return AppTest.from_string(
            '''
import streamlit as st
import components.account as page
user = {
    "id": 1, "name": "Compte test", "email": "compte@example.test", "plan": "free",
    "onboarding_completed": 1, "user_type": "Premier acheteur",
    "user_objective": "Acheter pour y habiter", "investment_horizon": "",
    "risk_tolerance": "", "analytics_consent": 0, "marketing_consent": 0,
}
original_progress = page.progress
original_is_authenticated = page.is_authenticated
original_current_user = page.current_user
original_count_analyses = page.count_analyses
original_quota_is_enforced = page.quota_is_enforced
original_quota_status = page.quota_status
original_can_use = page.can_use
original_export_user_data = page.export_user_data
try:
    page.is_authenticated = lambda: True
    page.current_user = lambda: user
    page.count_analyses = lambda _user_id: 0
    page.quota_is_enforced = lambda _database_path: False
    page.quota_status = lambda *_args: {"label": "1 estimation complète restante ce mois-ci"}
    page.can_use = lambda *_args: True
    page.export_user_data = lambda *_args: b"{}"
    page.progress = lambda _user_id, _database_path, **values: st.session_state.__setitem__("account_preference_capture", values)
    page.show_account()
finally:
    page.progress = original_progress
    page.is_authenticated = original_is_authenticated
    page.current_user = original_current_user
    page.count_analyses = original_count_analyses
    page.quota_is_enforced = original_quota_is_enforced
    page.quota_status = original_quota_status
    page.can_use = original_can_use
    page.export_user_data = original_export_user_data
'''
        ).run(timeout=20)

    def test_preferences_are_saved_explicitly_for_future_analyses(self):
        app = self._app()
        app.selectbox(key="account_profile").set_value("Investisseur locatif").run(timeout=20)
        app.selectbox(key="account_objective").set_value("Investir et louer").run(timeout=20)
        app.selectbox(key="account_horizon").set_value("2 à 5 ans").run(timeout=20)
        app.selectbox(key="account_risk").set_value("Modéré").run(timeout=20)
        app.checkbox(key="account_analytics_consent").set_value(True).run(timeout=20)
        app.button(key="save_account_preferences").click().run(timeout=20)
        self.assertEqual(
            app.session_state["account_preference_capture"],
            {
                "user_type": "Investisseur locatif", "user_objective": "Investir et louer",
                "investment_horizon": "2 à 5 ans", "risk_tolerance": "Modéré",
                "analytics_consent": 1, "marketing_consent": 0,
            },
        )
        self.assertTrue(any("Préférences enregistrées" in item.value for item in app.success))

    def test_profile_and_objective_remain_required_in_preferences(self):
        app = self._app()
        app.selectbox(key="account_profile").set_value("").run(timeout=20)
        app.button(key="save_account_preferences").click().run(timeout=20)
        self.assertIn("Choisissez un profil et un objectif principal.", [item.value for item in app.error])
        self.assertNotIn("account_preference_capture", app.session_state)


if __name__ == "__main__":
    unittest.main()
