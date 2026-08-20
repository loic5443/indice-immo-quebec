"""Streamlit regressions for Premium-only factual in-app alerts."""

import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database, save_analysis
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

    def test_alert_can_reopen_only_its_own_saved_dossier(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "alerts.sqlite"
            initialize_database(database_path)
            created, _ = create_user("Compte test", "alerts@example.test", "Motdepasse1", database_path)
            self.assertTrue(created)
            user = authenticate_user("alerts@example.test", "Motdepasse1", database_path)
            user["plan"] = "premium"
            analysis_id = save_analysis(user["id"], "Dossier de test", {
                "price": 400_000, "down_payment": 80_000, "rental_income": 2_500,
                "monthly_expenses": 2_000, "cash_flow": 120, "cash_on_cash_return": 3.0,
                "capitalization_rate": 5.0, "debt_service_coverage_ratio": 1.1,
                "resilience": {"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": -30}}]},
            }, database_path)
            analysis = {**_ANALYSIS, "id": analysis_id}
            import components.alerts as page
            original_path = page.DATABASE_PATH
            try:
                source = (
                    "from pathlib import Path\n"
                    "import components.alerts as page\n"
                    f"page.DATABASE_PATH = Path({str(database_path)!r})\n"
                    f"page.show_alert_center({user!r}, {[analysis]!r})\n"
                )
                app = AppTest.from_string(source).run(timeout=20)
                app.button(key=f"alert_open_{analysis_id}").click().run(timeout=20)
                self.assertEqual(app.session_state["main_navigation"], "Analyser")
                self.assertEqual(app.session_state["analysis_reopen_pending"]["owner_id"], user["id"])
            finally:
                page.DATABASE_PATH = original_path


if __name__ == "__main__":
    unittest.main()
