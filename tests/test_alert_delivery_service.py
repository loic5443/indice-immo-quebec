"""Focused regression tests for consented, idempotent alert-email delivery."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database, save_analysis
from services.alert_delivery_service import deliver_alerts_for_all_users, deliver_alerts_for_user
from services.alert_email_service import set_alert_email_consent
from services.dossier_tracking_service import set_dossier_tracking


ENVIRONMENT = {
    "IMMORADAR_ALERT_DELIVERY_ENABLED": "true",
    "BREVO_API_KEY": "test-key",
    "BREVO_SENDER_EMAIL": "sender@example.test",
}


class AlertDeliveryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database_path = Path(self.temp.name) / "alerts.sqlite"
        initialize_database(self.database_path)
        self.alice = self._user("Alice", "alice@example.test")
        self.bob = self._user("Bob", "bob@example.test")
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("UPDATE users SET plan = 'premium' WHERE id IN (?, ?)", (self.alice["id"], self.bob["id"]))
            connection.commit()
        self.first_id, self.latest_id = self._create_tracked_history(self.alice["id"])

    def tearDown(self):
        self.temp.cleanup()

    def _user(self, name: str, email: str) -> dict:
        created, _ = create_user(name, email, "Motdepasse1", self.database_path)
        self.assertTrue(created)
        user = authenticate_user(email, "Motdepasse1", self.database_path)
        self.assertIsNotNone(user)
        return user

    def _create_tracked_history(self, user_id: int) -> tuple[int, int]:
        values = {
            "price": 400_000, "down_payment": 80_000, "rental_income": 2_500,
            "monthly_expenses": 2_000, "cash_flow": 100, "cash_on_cash_return": 3.0,
            "capitalization_rate": 5.0, "debt_service_coverage_ratio": 1.1,
        }
        first_id = save_analysis(user_id, "Dossier suivi", values, self.database_path)
        latest_id = save_analysis(user_id, "Dossier suivi", values, self.database_path)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                "UPDATE analyses SET created_at = ?, immovalue_json = ?, official_role_snapshot_json = ?, resilience_json = ? WHERE id = ?",
                (
                    "2026-01-01 10:00 UTC",
                    json.dumps({"available": True, "estimated_value": 400_000, "confidence": 60}),
                    json.dumps({"total_value": 350_000, "role_year": 2025}),
                    json.dumps({"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": 30}}]}),
                    first_id,
                ),
            )
            connection.execute(
                "UPDATE analyses SET created_at = ?, immovalue_json = ?, official_role_snapshot_json = ?, resilience_json = ? WHERE id = ?",
                (
                    "2026-02-01 10:00 UTC",
                    json.dumps({"available": True, "estimated_value": 420_000, "confidence": 60}),
                    json.dumps({"total_value": 360_000, "role_year": 2026}),
                    json.dumps({"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": -20}}]}),
                    latest_id,
                ),
            )
            connection.commit()
        set_dossier_tracking(user_id, latest_id, True, self.database_path)
        return first_id, latest_id

    def test_delivery_requires_the_separate_email_consent(self):
        calls = []
        result = deliver_alerts_for_user(
            self.alice["id"], self.database_path, environment=ENVIRONMENT,
            sender=lambda *args, **kwargs: calls.append((args, kwargs)),
        )
        self.assertEqual(result.status, "not_eligible")
        self.assertEqual(calls, [])

    def test_one_generic_digest_is_sent_once_for_new_factual_alerts(self):
        self.assertTrue(set_alert_email_consent(self.alice["id"], True, self.database_path))
        sent = []

        def fake_sender(recipient, subject, content, *, environment):
            sent.append((recipient, subject, content, environment))

        first = deliver_alerts_for_user(self.alice["id"], self.database_path, environment=ENVIRONMENT, sender=fake_sender)
        second = deliver_alerts_for_user(self.alice["id"], self.database_path, environment=ENVIRONMENT, sender=fake_sender)
        self.assertEqual(first.status, "sent")
        self.assertGreaterEqual(first.delivered, 1)
        self.assertEqual(second.status, "already_processed")
        self.assertEqual(len(sent), 1)
        self.assertNotIn("Dossier suivi", sent[0][2])
        self.assertNotIn("400 000", sent[0][2])
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT alert_fingerprint, outcome FROM alert_delivery_log WHERE user_id = ? AND alert_fingerprint != ?",
                (self.alice["id"], "brevo-email-test-v1"),
            ).fetchall()
        self.assertTrue(rows)
        self.assertTrue(all(len(row[0]) == 64 and row[1] == "sent" for row in rows))

    def test_failure_is_logged_without_auto_resend(self):
        self.assertTrue(set_alert_email_consent(self.alice["id"], True, self.database_path))
        attempts = []

        def failing_sender(*_args, **_kwargs):
            attempts.append(True)
            raise OSError("network unavailable")

        first = deliver_alerts_for_user(self.alice["id"], self.database_path, environment=ENVIRONMENT, sender=failing_sender)
        second = deliver_alerts_for_user(self.alice["id"], self.database_path, environment=ENVIRONMENT, sender=failing_sender)
        self.assertEqual(first.status, "failed")
        self.assertEqual(second.status, "already_processed")
        self.assertEqual(len(attempts), 1)

    def test_worker_only_processes_opted_in_accounts(self):
        self.assertTrue(set_alert_email_consent(self.alice["id"], True, self.database_path))
        sent = []
        results = deliver_alerts_for_all_users(
            self.database_path,
            environment=ENVIRONMENT,
            sender=lambda *args, **kwargs: sent.append((args, kwargs)),
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "sent")
        self.assertEqual(len(sent), 1)


if __name__ == "__main__":
    unittest.main()
