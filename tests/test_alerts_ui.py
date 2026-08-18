"""Streamlit regressions for Premium-only factual in-app alerts."""

import unittest

from streamlit.testing.v1 import AppTest


_ANALYSIS = {
    "id": 1,
    "property_name": "Dossier de test",
    "created_at": "2026-02-01 10:00 UTC",
    "cash_flow": 120,
    "immovalue_json": "{}",
    "official_role_snapshot_json": "{}",
    "resilience_json": '{"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": -30}}]}',
}


class AlertsUiTests(unittest.TestCase):
    def _app(self, plan):
        return AppTest.from_string(
            "import components.alerts as page\n"
            f"page.show_alert_center({{'plan': '{plan}', 'role': 'user'}}, {[_ANALYSIS]!r})"
        ).run(timeout=20)

    def test_free_account_keeps_alerts_locked(self):
        app = self._app("free")
        text = " ".join(item.value for item in app.markdown)
        self.assertIn("APERÇU PREMIUM", text)
        self.assertNotIn("fragilise le flux", text)

    def test_premium_account_sees_calculable_alert_without_email(self):
        app = self._app("premium")
        self.assertFalse(app.exception)
        self.assertIn("Une hausse de taux fragilise le flux mensuel", [item.value for item in app.subheader])
        self.assertTrue(any("Aucun courriel" in item.value for item in app.caption))


if __name__ == "__main__":
    unittest.main()
