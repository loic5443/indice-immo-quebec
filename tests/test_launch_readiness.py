import json
import tempfile
import unittest
from pathlib import Path
from data.database import initialize_database
from scripts.launch_readiness import check_readiness


class ReadinessTests(unittest.TestCase):
    def test_diagnostics_are_offline_and_redact_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "launch.sqlite"
            initialize_database(path)
            result = check_readiness(path, {"IMMORADAR_BILLING_ENABLED": "1", "STRIPE_SECRET_KEY": "private-material"})
            self.assertEqual(result["database"], "verified")
            self.assertEqual(result["migrations"], "current")
            self.assertEqual(result["billing"], "incomplete_configuration")
            self.assertNotIn("private-material", json.dumps(result))

    def test_missing_database_is_not_created_by_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.sqlite"
            self.assertEqual(check_readiness(path, {})["database"], "unavailable_or_invalid")
            self.assertFalse(path.exists())
