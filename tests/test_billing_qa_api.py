import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from data.database import initialize_database, create_user
from services.billing_api import app
from services.billing_service import effective_plan
from scripts.render_server import prepare_sandbox_database


class SandboxWebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.production = Path(self.temp.name) / "production.sqlite"
        self.qa = Path(self.temp.name) / "cenlio-stripe-qa.sqlite"
        for database in (self.production, self.qa):
            initialize_database(database)
            create_user("Test", "qa@example.test", "a-valid-test-password", database)
        with sqlite3.connect(self.qa) as connection:
            connection.execute("INSERT INTO billing_accounts(user_id,customer_id,mode) VALUES(1,'cus_qa','test')")
        self.env = {
            "IMMORADAR_STRIPE_QA_WEBHOOK_ENABLED": "1",
            "IMMORADAR_PUBLIC_URL": "https://cenlio.example",
            "STRIPE_TEST_SECRET_KEY": "rk_test_placeholder",
            "STRIPE_TEST_WEBHOOK_SECRET": "whsec_test_placeholder",
            "STRIPE_TEST_PREMIUM_PRICE_ID": "price_qa",
            # Commercial settings must never be used for sandbox processing.
            "STRIPE_SECRET_KEY": "rk_live_unused",
            "STRIPE_WEBHOOK_SECRET": "whsec_live_unused",
            "IMMORADAR_BILLING_ENABLED": "0",
        }
        env_patch = patch.dict(os.environ, self.env, clear=True)
        env_patch.start()
        self.addCleanup(env_patch.stop)
        path_patch = patch("services.billing_qa_api.DATABASE_PATH", self.production)
        path_patch.start()
        self.addCleanup(path_patch.stop)
        self.client = TestClient(app)
        self.subscription = {
            "id": "sub_qa", "customer": "cus_qa", "livemode": False,
            "metadata": {"immoradar_user_id": "1"}, "status": "active",
            "items": {"data": [{"price": {"id": "price_qa"}, "quantity": 1,
                                  "current_period_end": int(time.time()) + 3600}]},
        }
        self.retrieve = Mock(side_effect=lambda *_: self.subscription)
        self.provider = SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(retrieve=self.retrieve)))

    def send(self, event_id="evt_qa", live=False, signature=None):
        payload = json.dumps({"id": event_id, "type": "customer.subscription.updated", "livemode": live,
                              "data": {"object": {"id": "sub_qa"}}}).encode()
        stamp = int(time.time())
        digest = hmac.new(self.env["STRIPE_TEST_WEBHOOK_SECRET"].encode(), str(stamp).encode()+b"."+payload, hashlib.sha256).hexdigest()
        with patch("services.billing_service._provider", return_value=self.provider):
            return self.client.post("/stripe/test-webhook", content=payload,
                                    headers={"stripe-signature": signature or f"t={stamp},v1={digest}"})

    def test_signed_events_activate_and_remove_premium_only_in_qa_database(self):
        with self.assertLogs("uvicorn.error", level="INFO") as logs:
            self.assertEqual(self.send().status_code, 200)
        self.assertIn("premium_accounts=1", logs.output[0])
        mode = {"IMMORADAR_BILLING_ENABLED": "1", "IMMORADAR_BILLING_MODE": "test"}
        self.assertEqual(effective_plan(1, "free", self.qa, environment=mode), "premium")
        self.assertEqual(effective_plan(1, "free", self.production, environment=mode), "free")
        self.assertEqual(self.send().json(), {"status": "duplicate"})
        self.assertEqual(self.retrieve.call_count, 1)
        self.subscription["status"] = "canceled"
        self.assertEqual(self.send("evt_canceled").status_code, 200)
        self.assertEqual(effective_plan(1, "free", self.qa, environment=mode), "free")

    def test_forged_or_live_event_cannot_reach_provider(self):
        self.assertEqual(self.send(signature="invalid").status_code, 400)
        self.assertEqual(self.send(live=True).status_code, 400)
        self.retrieve.assert_not_called()

    def test_disabled_endpoint_and_live_credentials_fail_closed(self):
        with patch.dict(os.environ, {"IMMORADAR_STRIPE_QA_WEBHOOK_ENABLED": "0"}):
            self.assertEqual(self.send().status_code, 404)
        with patch.dict(os.environ, {"STRIPE_TEST_SECRET_KEY": "rk_live_wrong"}):
            self.assertEqual(self.send().status_code, 503)
        self.retrieve.assert_not_called()

    def test_large_body_is_not_processed(self):
        with patch("services.billing_qa_api.handle_sandbox_event") as handler:
            self.assertEqual(self.client.post("/stripe/test-webhook", content=b"x"*1_000_001).status_code, 413)
        handler.assert_not_called()

    def test_shell_database_permissions_change_only_fixed_qa_file(self):
        with patch("scripts.render_server.os.chown") as chown:
            prepare_sandbox_database(self.production, 1000, 1000)
        chown.assert_called_once_with(self.qa, 1000, 1000)
        self.assertEqual(self.qa.stat().st_mode & 0o777, 0o600)
        self.qa.unlink()
        self.qa.symlink_to(self.production)
        with patch("scripts.render_server.os.chown") as chown, self.assertRaises(ValueError):
            prepare_sandbox_database(self.production, 1000, 1000)
        chown.assert_not_called()

    def test_database_alias_to_production_is_rejected(self):
        self.qa.unlink()
        self.qa.symlink_to(self.production)
        self.assertEqual(self.send().status_code, 503)
        self.retrieve.assert_not_called()
