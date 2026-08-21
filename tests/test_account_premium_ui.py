"""Account-level conversion copy stays honest about the beta quota."""

import unittest


class AccountPremiumUiTests(unittest.TestCase):
    def test_free_account_sees_beta_quota_truth_and_concrete_premium_outcome(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string('''
import components.account as page
user = {
    "id": 1, "name": "Compte bêta", "email": "compte@example.test", "plan": "free",
    "onboarding_completed": 1, "user_type": "Propriétaire", "investment_horizon": "2 à 5 ans",
    "risk_tolerance": "Modéré",
}
page.is_authenticated = lambda: True
page.current_user = lambda: user
page.count_analyses = lambda _user_id: 2
page.quota_is_enforced = lambda _database_path: False
page.quota_status = lambda *_args: {"label": "1 estimation complète restante ce mois-ci"}
page.can_use = lambda *_args: False
page.export_user_data = lambda *_args: b"{}"
page.show_account()
''').run(timeout=20)
        self.assertFalse(app.exception)
        text = " ".join(item.value for item in app.caption) + " ".join(item.value for item in app.markdown)
        self.assertIn("Quota mensuel en aperçu", text)
        self.assertIn("Passez du calcul ponctuel", text)
        self.assertIn("Découvrir Premium", [button.label for button in app.button])

    def test_account_summary_escapes_user_text_before_html_rendering(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string('''
import components.account as page
user = {
    "id": 1, "name": "<script>unsafe</script>", "email": "<b>courriel@example.test</b>", "plan": "free",
    "onboarding_completed": 1, "user_type": "Propriétaire", "investment_horizon": "2 à 5 ans",
    "risk_tolerance": "Modéré",
}
page.is_authenticated = lambda: True
page.current_user = lambda: user
page.count_analyses = lambda _user_id: 0
page.quota_is_enforced = lambda _database_path: False
page.quota_status = lambda *_args: {"label": "1 estimation complète restante ce mois-ci"}
page.can_use = lambda *_args: True
page.export_user_data = lambda *_args: b"{}"
page.show_account()
''').run(timeout=20)
        self.assertFalse(app.exception)
        markup = " ".join(item.value for item in app.markdown)
        self.assertIn("&lt;script&gt;unsafe&lt;/script&gt;", markup)
        self.assertIn("&lt;b&gt;courriel@example.test&lt;/b&gt;", markup)


if __name__ == "__main__":
    unittest.main()
