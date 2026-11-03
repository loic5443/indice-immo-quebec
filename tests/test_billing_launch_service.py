from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import stripe

from services.billing_launch_service import prepare_launch


class LaunchPreflightTests(unittest.TestCase):
    def setUp(self):
        self.env = {"STRIPE_SECRET_KEY": "rk_live_placeholder", "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
                    "STRIPE_PREMIUM_PRICE_ID": "price_live", "IMMORADAR_PUBLIC_URL": "https://cenlio.example",
                    "STRIPE_LAUNCH_PORTAL_ID": "bpc_live", "STRIPE_LAUNCH_WEBHOOK_ID": "we_live"}
        self.portal_config = SimpleNamespace(retrieve=Mock(return_value={"active": True, "is_default": True,
            "livemode": True, "features": {"subscription_cancel": {"enabled": True, "mode": "at_period_end"}}}), update=Mock())
        self.hooks = SimpleNamespace(retrieve=Mock(return_value={"livemode": True, "status": "enabled",
            "url": "https://cenlio.example/stripe/webhook", "enabled_events": ["invoice.paid"]}), update=Mock())
        self.sessions = SimpleNamespace(create=Mock(return_value={"id": "cs_live", "livemode": True, "status": "open"}),
                                        expire=Mock(return_value={"status": "expired"}))
        self.customers = SimpleNamespace(create=Mock(return_value={"id": "cus_live"}), delete=Mock())
        self.client = SimpleNamespace(v1=SimpleNamespace(
            prices=SimpleNamespace(retrieve=Mock(return_value={"active": True, "livemode": True, "currency": "cad",
                "unit_amount": 1499, "type": "recurring", "recurring": {"interval": "month", "interval_count": 1}})),
            billing_portal=SimpleNamespace(configurations=self.portal_config,
                sessions=SimpleNamespace(create=Mock(return_value={"livemode": True}))),
            webhook_endpoints=self.hooks, customers=self.customers, checkout=SimpleNamespace(sessions=self.sessions),
            charges=SimpleNamespace(list=Mock()), invoices=SimpleNamespace(list=Mock()), invoice_payments=SimpleNamespace(list=Mock())))

    def test_real_checkout_is_expired_and_customer_removed_without_a_payment(self):
        report = prepare_launch(self.env, self.client)
        self.assertEqual(report["status"], "ready")
        self.assertIs(report["charged"], False)
        self.sessions.expire.assert_called_once_with("cs_live")
        self.customers.delete.assert_called_once_with("cus_live")
        self.assertNotIn("rk_live_placeholder", str(report))
        events = self.hooks.update.call_args.args[1]["enabled_events"]
        for kind in ("invoice.paid", "charge.refunded", "charge.dispute.created", "radar.early_fraud_warning.created", "customer.created"):
            self.assertIn(kind, events)

    def test_permission_failure_stops_without_creating_a_live_checkout_or_leaking_errors(self):
        self.hooks.update.side_effect = stripe.PermissionError("private provider detail", http_status=403)
        report = prepare_launch(self.env, self.client)
        self.assertEqual(report, {"status": "blocked", "stage": "webhook_configuration", "http_status": 403})
        self.customers.create.assert_not_called()
        self.sessions.create.assert_not_called()

    def test_failed_checkout_still_removes_its_customer(self):
        self.sessions.create.side_effect = stripe.PermissionError("private", http_status=403)
        self.assertEqual(prepare_launch(self.env, self.client)["status"], "blocked")
        self.customers.delete.assert_called_once_with("cus_live")

    def test_cleanup_failure_prevents_activation(self):
        self.customers.delete.side_effect = stripe.APIConnectionError("private")
        self.assertEqual(prepare_launch(self.env, self.client), {"status": "blocked", "stage": "customer_cleanup"})

    def test_wrong_price_never_creates_a_customer_or_checkout(self):
        self.client.v1.prices.retrieve.return_value["unit_amount"] = 2900
        self.assertEqual(prepare_launch(self.env, self.client), {"status": "blocked", "stage": "price", "error_type": "ValueError"})
        self.customers.create.assert_not_called()
