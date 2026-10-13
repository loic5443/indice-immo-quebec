import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from data.database import initialize_database
from services.operations_service import run_operations


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "source.sqlite"
        initialize_database(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_cycle_performs_no_delivery_or_backup(self):
        sender = Mock()
        result = run_operations(self.db, self.root / "backups", environment={}, deliver=sender)
        self.assertEqual(result, {"backup": "disabled", "alerts": "disabled"})
        sender.assert_not_called()
        self.assertFalse((self.root / "backups").exists())

    def test_explicit_backups_are_verified_and_never_overwrite(self):
        for _ in range(2):
            result = run_operations(self.db, self.root / "backups", environment={"IMMORADAR_BACKUPS_ENABLED": "1"}, now=1000)
            self.assertEqual(result["backup"], "verified")
        self.assertEqual(len(list((self.root / "backups").glob("*.sqlite"))), 2)

    def test_alert_delivery_returns_only_aggregates(self):
        sender = Mock(return_value=[SimpleNamespace(status="delivered", delivered=2)])
        env = {"IMMORADAR_ALERT_DELIVERY_ENABLED": "true", "BREVO_API_KEY": "placeholder", "BREVO_SENDER_EMAIL": "sender@example.test"}
        result = run_operations(self.db, self.root / "backups", environment=env, deliver=sender)
        self.assertEqual(result["alerts"], {"delivered": 1})
        self.assertEqual(result["delivered"], 2)
        self.assertNotIn("email", str(result))

    def test_worker_error_is_redacted(self):
        sender = Mock(side_effect=RuntimeError("private key"))
        env = {"IMMORADAR_ALERT_DELIVERY_ENABLED": "true", "BREVO_API_KEY": "placeholder", "BREVO_SENDER_EMAIL": "sender@example.test"}
        result = run_operations(self.db, self.root / "backups", environment=env, deliver=sender)
        self.assertEqual(result["alerts"], "failed")
        self.assertNotIn("private", str(result))
