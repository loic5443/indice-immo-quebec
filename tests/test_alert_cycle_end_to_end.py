"""End-to-end regression for a factual tracked-dossier alert cycle.

The test uses a temporary SQLite database and a local sender double.  It
verifies the same boundary used with Brevo without sending a real email or
putting account, dossier or financial data in a test log.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data.database import authenticate_user, create_user, initialize_database, save_analysis
from services.alert_delivery_service import AlertDeliveryResult, deliver_alerts_for_user
from services.alert_email_service import set_alert_email_consent
from services.dossier_tracking_service import set_dossier_tracking


SAFE_ENVIRONMENT = {
    "IMMORADAR_ALERT_DELIVERY_ENABLED": "true",
    "BREVO_API_KEY": "test-key",
    "BREVO_SENDER_EMAIL": "sender@example.test",
}


class AlertCycleEndToEndTests(unittest.TestCase):
    """A saved change is private in-app, with one opt-in generic email."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database_path = Path(self.temp.name) / "alert-cycle.sqlite"
        initialize_database(self.database_path)
        created, _ = create_user("Compte de test", "alert-cycle@example.test", "Motdepasse1", self.database_path)
        self.assertTrue(created)
        self.user = authenticate_user("alert-cycle@example.test", "Motdepasse1", self.database_path)
        self.assertIsNotNone(self.user)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("UPDATE users SET plan = 'premium' WHERE id = ?", (self.user["id"],))
            connection.commit()
        self.first_id, self.latest_id = self._create_changed_tracked_dossier()

    def tearDown(self):
        self.temp.cleanup()

    def _create_changed_tracked_dossier(self) -> tuple[int, int]:
        values = {
            "price": 400_000, "down_payment": 80_000, "rental_income": 2_500,
            "monthly_expenses": 2_000, "cash_flow": 100, "cash_on_cash_return": 3.0,
            "capitalization_rate": 5.0, "debt_service_coverage_ratio": 1.1,
        }
        first_id = save_analysis(self.user["id"], "Dossier suivi de test", values, self.database_path)
        latest_id = save_analysis(self.user["id"], "Dossier suivi de test", values, self.database_path)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE analyses SET created_at=?, immovalue_json=?, official_role_snapshot_json=?, resilience_json=? WHERE id=?",
                (
                    "2026-01-01 10:00 UTC",
                    json.dumps({"available": True, "estimated_value": 400_000, "confidence": 60}),
                    json.dumps({"total_value": 350_000, "role_year": 2025}),
                    json.dumps({"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": 30}}]}),
                    first_id,
                ),
            )
            connection.execute(
                "UPDATE analyses SET created_at=?, immovalue_json=?, official_role_snapshot_json=?, resilience_json=? WHERE id=?",
                (
                    "2026-02-01 10:00 UTC",
                    json.dumps({"available": True, "estimated_value": 420_000, "confidence": 60}),
                    json.dumps({"total_value": 360_000, "role_year": 2026}),
                    json.dumps({"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": -20}}]}),
                    latest_id,
                ),
            )
            connection.commit()
        set_dossier_tracking(self.user["id"], latest_id, True, self.database_path)
        return first_id, latest_id

    def test_tracked_change_delivers_one_generic_email_and_stays_visible_in_app(self):
        self.assertTrue(set_alert_email_consent(self.user["id"], True, self.database_path))
        deliveries = []

        def sender(recipient, subject, content, *, environment):
            deliveries.append((recipient, subject, content, environment))

        first_delivery = deliver_alerts_for_user(
            self.user["id"], self.database_path, environment=SAFE_ENVIRONMENT, sender=sender,
        )
        second_delivery = deliver_alerts_for_user(
            self.user["id"], self.database_path, environment=SAFE_ENVIRONMENT, sender=sender,
        )
        self.assertEqual(first_delivery.status, "sent")
        self.assertGreater(first_delivery.delivered, 0)
        self.assertEqual(second_delivery.status, "already_processed")
        self.assertEqual(len(deliveries), 1)
        _, subject, content, _ = deliveries[0]
        self.assertEqual(subject, "ImmoRadar — une alerte est disponible")
        self.assertNotIn("Dossier suivi de test", content)
        self.assertNotIn("420 000", content)
        self.assertNotIn("alert-cycle@example.test", content)

        with sqlite3.connect(self.database_path) as connection:
            outcomes = connection.execute(
                "SELECT outcome FROM alert_delivery_log WHERE user_id=? AND channel='email'",
                (self.user["id"],),
            ).fetchall()
        self.assertTrue(outcomes)
        self.assertTrue(all(outcome[0] == "sent" for outcome in outcomes))

        from repositories.sqlite_repository import SQLiteRepository

        analyses = SQLiteRepository(self.database_path).list_analyses(self.user["id"])
        app = AppTest.from_string(
            "import components.alerts as page\n"
            "from services.alert_delivery_service import AlertDeliveryResult\n"
            f"page.DATABASE_PATH = {str(self.database_path)!r}\n"
            "page.deliver_alerts_for_user = lambda *_args, **_kwargs: AlertDeliveryResult('already_processed')\n"
            f"page.show_alert_center({{\"id\": {self.user['id']}, \"plan\": \"premium\", \"role\": \"user\", \"alert_email_consent\": True}}, {analyses!r})\n"
        ).run(timeout=20)
        self.assertFalse(app.exception)
        alert_titles = [item.value for item in app.subheader]
        self.assertTrue(any("ImmoValue" in title for title in alert_titles))
        self.assertTrue(any("rôle municipal" in title for title in alert_titles))
        self.assertTrue(any("Dossier suivi de test" in item.value for item in app.caption))
        self.assertIn("Gérer mes alertes par courriel", [button.label for button in app.button])


if __name__ == "__main__":
    unittest.main()
