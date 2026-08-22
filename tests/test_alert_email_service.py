"""Privacy checks for the dormant-by-default Premium email-alert foundation."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database
from providers.brevo_email import BrevoUnavailable, delivery_status, send_email
from services.alert_email_service import has_alert_email_consent, send_test_alert_email, set_alert_email_consent


class AlertEmailServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database_path = Path(self.temp.name) / "alerts.sqlite"
        initialize_database(self.database_path)
        created, _ = create_user("Compte test", "alert-email@example.test", "motdepasse-solide", self.database_path)
        self.assertTrue(created)
        self.user = authenticate_user("alert-email@example.test", "motdepasse-solide", self.database_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_migration_defaults_to_no_email_consent_and_is_separate_from_marketing(self):
        self.assertFalse(has_alert_email_consent(self.user["id"], self.database_path))
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT alert_email_consent, marketing_consent FROM users WHERE id = ?", (self.user["id"],)).fetchone()
        self.assertEqual(row, (0, 0))

    def test_consent_can_be_withdrawn_immediately(self):
        self.assertTrue(set_alert_email_consent(self.user["id"], True, self.database_path))
        self.assertTrue(has_alert_email_consent(self.user["id"], self.database_path))
        self.assertTrue(set_alert_email_consent(self.user["id"], False, self.database_path))
        self.assertFalse(has_alert_email_consent(self.user["id"], self.database_path))

    def test_transport_is_inert_without_explicit_local_enablement(self):
        self.assertEqual(delivery_status({}), "disabled")
        with self.assertRaises(BrevoUnavailable):
            send_email("recipient@example.test", "Sujet", "<p>Contenu</p>", environment={})

    def test_enabled_transport_without_configuration_still_never_calls_network(self):
        calls = []

        def opener(_request, timeout):
            calls.append(timeout)
            raise AssertionError("Le transport ne doit pas être appelé sans configuration.")

        environment = {"IMMORADAR_ALERT_DELIVERY_ENABLED": "true"}
        self.assertEqual(delivery_status(environment), "not_configured")
        with self.assertRaises(BrevoUnavailable):
            send_email("recipient@example.test", "Sujet", "<p>Contenu</p>", environment=environment, opener=opener)
        self.assertEqual(calls, [])

    def test_test_delivery_requires_saved_consent_and_keeps_personal_data_out_of_log(self):
        sent = []

        def fake_sender(recipient, subject, content, *, environment):
            sent.append((recipient, subject, content, environment))

        environment = {
            "IMMORADAR_ALERT_DELIVERY_ENABLED": "true",
            "BREVO_API_KEY": "test-key",
            "BREVO_SENDER_EMAIL": "sender@example.test",
        }
        self.assertEqual(
            send_test_alert_email(self.user["id"], self.database_path, environment=environment, sender=fake_sender),
            "no_consent",
        )
        self.assertEqual(sent, [])

        self.assertTrue(set_alert_email_consent(self.user["id"], True, self.database_path))
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("UPDATE users SET plan = 'premium' WHERE id = ?", (self.user["id"],))
            connection.commit()
        self.assertEqual(
            send_test_alert_email(self.user["id"], self.database_path, environment=environment, sender=fake_sender),
            "sent",
        )
        self.assertEqual(len(sent), 1)
        self.assertNotIn("alert-email@example.test", sent[0][2])
        self.assertEqual(
            send_test_alert_email(self.user["id"], self.database_path, environment=environment, sender=fake_sender),
            "already_sent",
        )
        self.assertEqual(len(sent), 1)
        with sqlite3.connect(self.database_path) as connection:
            log = connection.execute(
                "SELECT alert_fingerprint, outcome FROM alert_delivery_log WHERE user_id = ?",
                (self.user["id"],),
            ).fetchone()
        self.assertEqual(log, ("brevo-email-test-v1", "sent"))


if __name__ == "__main__":
    unittest.main()
