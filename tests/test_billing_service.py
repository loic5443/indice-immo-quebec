"""Payment lifecycle contracts, using an isolated DB and provider double."""
import hashlib
import hmac
import json
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import stripe

from data.database import initialize_database, create_user, get_user
from repositories.sqlite_repository import SQLiteRepository
from services.billing_service import (
    BillingError, billing_config, premium_offer, create_checkout, confirm_checkout,
    create_portal, refresh_subscription, process_webhook, effective_plan, billing_account,
)
from services.privacy_service import delete_account


ENV = {"IMMORADAR_BILLING_ENABLED": "1", "IMMORADAR_BILLING_MODE": "test",
       "STRIPE_SECRET_KEY": "sk_test_placeholder", "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
       "STRIPE_PREMIUM_PRICE_ID": "price_premium", "IMMORADAR_PUBLIC_URL": "https://immoradar.example"}


def signed_payload(kind, obj, event_id="evt_1", live=False):
    payload = json.dumps({"id": event_id, "type": kind, "livemode": live, "data": {"object": obj}}).encode()
    stamp = int(time.time())
    digest = hmac.new(ENV["STRIPE_WEBHOOK_SECRET"].encode(), str(stamp).encode() + b"." + payload, hashlib.sha256).hexdigest()
    return payload, f"t={stamp},v1={digest}"


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "billing.sqlite"
        initialize_database(self.db)
        create_user("Compte 1", "one@example.test", "long-password-test", self.db)
        create_user("Compte 2", "two@example.test", "long-password-test", self.db)
        self.price = {"id": "price_premium", "active": True, "livemode": False, "currency": "cad",
                      "unit_amount": 2900, "type": "recurring", "recurring": {"interval": "month", "interval_count": 1}}
        self.subscription = {"id": "sub_1", "customer": "cus_1", "livemode": False,
                             "metadata": {"immoradar_user_id": "1"}, "status": "active",
                             "items": {"data": [{"price": {"id": "price_premium"}, "quantity": 1,
                                                  "current_period_end": int(time.time()) + 3600}]}}
        self.session = {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/test", "status": "open",
                        "mode": "subscription", "livemode": False, "client_reference_id": "1",
                        "customer": "cus_1", "subscription": "sub_1", "payment_status": "unpaid"}
        self.client = SimpleNamespace(v1=SimpleNamespace(
            prices=SimpleNamespace(retrieve=Mock(return_value=self.price)),
            customers=SimpleNamespace(create=Mock(return_value={"id": "cus_1"})),
            subscriptions=SimpleNamespace(list=Mock(return_value={"data": [], "has_more": False}), retrieve=Mock(return_value=self.subscription)),
            checkout=SimpleNamespace(sessions=SimpleNamespace(create=Mock(return_value=self.session), retrieve=Mock(return_value=self.session))),
            billing_portal=SimpleNamespace(sessions=SimpleNamespace(create=Mock(return_value={"url": "https://billing.stripe.com/p/session/test"}))),
        ))

    def tearDown(self):
        self.temp.cleanup()

    def checkout(self):
        return create_checkout(1, self.db, ENV, self.client)

    def event(self, kind="customer.subscription.updated", obj=None, **kw):
        payload, signature = signed_payload(kind, obj or self.subscription, **kw)
        return process_webhook(payload, signature, self.db, ENV, self.client)

    def paid(self):
        self.checkout()
        self.session.update(status="complete", payment_status="paid")
        return confirm_checkout(1, "cs_test_1", self.db, ENV, self.client)

    def test_actual_sdk_objects_are_supported(self):
        self.client.v1.prices.retrieve.return_value = stripe.StripeObject.construct_from(self.price, None)
        self.assertEqual(premium_offer(ENV, self.client)["price_label"], "29,00 $ CA / mois")
        self.client.v1.checkout.sessions.create.return_value = stripe.StripeObject.construct_from(self.session, None)
        self.assertTrue(self.checkout().startswith("https://checkout.stripe.com/"))

    def test_disabled_billing_makes_no_provider_calls(self):
        self.assertIsNone(premium_offer({}, self.client))
        with self.assertRaises(BillingError):
            create_checkout(1, self.db, {}, self.client)
        self.client.v1.customers.create.assert_not_called()

    def test_config_requires_https_mode_matching_and_no_query_redirect(self):
        for patch in ({"IMMORADAR_PUBLIC_URL": "http://example.test"}, {"IMMORADAR_PUBLIC_URL": "https://user:pass@example.test"},
                      {"IMMORADAR_PUBLIC_URL": "https://example.test/?next=bad"}, {"IMMORADAR_BILLING_MODE": "live"},
                      {"STRIPE_WEBHOOK_SECRET": ""}):
            with self.subTest(patch=patch), self.assertRaises(BillingError):
                billing_config({**ENV, **patch})

    def test_restricted_keys_keep_test_and_live_modes_separate(self):
        for mode, key in (("test", "rk_test_placeholder"),
                          ("test", "rkcs_test_placeholder"),
                          ("live", "rk_live_placeholder")):
            with self.subTest(mode=mode, key=key):
                self.assertEqual(billing_config({**ENV, "IMMORADAR_BILLING_MODE": mode,
                                                 "STRIPE_SECRET_KEY": key}).mode, mode)
        for mode, key in (("live", "rk_test_placeholder"),
                          ("live", "rkcs_test_placeholder"),
                          ("test", "rk_live_placeholder"),
                          ("test", "pk_test_placeholder"),
                          ("live", "rkcs_live_placeholder")):
            with self.subTest(mode=mode, key=key), self.assertRaises(BillingError):
                billing_config({**ENV, "IMMORADAR_BILLING_MODE": mode, "STRIPE_SECRET_KEY": key})

    def test_price_is_retrieved_and_validated_before_checkout(self):
        self.assertEqual(premium_offer(ENV, self.client)["price_label"], "29,00 $ CA / mois")
        for patch in ({"active": False}, {"currency": "usd"}, {"livemode": True}, {"unit_amount": 0},
                      {"recurring": {"interval": "year", "interval_count": 1}}):
            with self.subTest(patch=patch):
                self.client.v1.prices.retrieve.return_value = {**self.price, **patch}
                with self.assertRaises(BillingError):
                    self.checkout()
        self.client.v1.customers.create.assert_not_called()

    def test_repeated_click_reuses_open_checkout(self):
        first = self.checkout()
        self.assertEqual(first, self.checkout())
        self.client.v1.checkout.sessions.create.assert_called_once()
        self.client.v1.customers.create.assert_called_once()
        params = self.client.v1.checkout.sessions.create.call_args.args[0]
        self.assertEqual(params["client_reference_id"], "1")
        self.assertEqual(params["line_items"], [{"price": "price_premium", "quantity": 1}])
        self.assertTrue(params["automatic_tax"]["enabled"])
        self.assertEqual(params["customer_update"], {"address": "auto"})
        self.assertEqual(params["locale"], "fr-CA")
        self.assertRegex(params["integration_identifier"], r"^immoradar-premium-[a-z]{8}$")
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "free")

    def test_timeout_retry_keeps_same_idempotency_key(self):
        self.client.v1.checkout.sessions.create.side_effect = stripe.APIConnectionError("secret provider detail")
        for _ in range(2):
            with self.assertRaises(BillingError) as raised:
                self.checkout()
            self.assertNotIn("secret provider detail", str(raised.exception))
        calls = self.client.v1.checkout.sessions.create.call_args_list
        self.assertEqual(calls[0].kwargs["options"], calls[1].kwargs["options"])
        self.assertEqual(calls[0].args[0], calls[1].args[0])

    def test_delayed_webhook_does_not_allow_second_subscription(self):
        self.checkout()
        self.client.v1.subscriptions.list.return_value = {"data": [{"status": "active"}]}
        with self.assertRaises(BillingError):
            self.checkout()
        self.client.v1.checkout.sessions.create.assert_called_once()

    def test_checkout_return_requires_payment_and_exact_owner(self):
        self.checkout()
        self.assertFalse(confirm_checkout(1, "cs_test_1", self.db, ENV, self.client))
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "free")
        self.session.update(status="complete", payment_status="paid")
        with self.assertRaises(BillingError):
            confirm_checkout(2, "cs_test_1", self.db, ENV, self.client)
        self.session["client_reference_id"] = "2"
        with self.assertRaises(BillingError):
            confirm_checkout(1, "cs_test_1", self.db, ENV, self.client)

    def test_paid_return_unlocks_until_verified_period_end(self):
        self.assertTrue(self.paid())
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "premium")
        self.assertEqual(effective_plan(2, "free", self.db, environment=ENV), "free")
        self.assertEqual(effective_plan(1, "free", self.db, now=int(time.time()) + 7200, environment=ENV), "free")
        self.assertEqual(get_user(1, self.db)["plan"], "premium")

    def test_wrong_price_or_quantity_cannot_unlock(self):
        self.checkout()
        self.subscription["items"]["data"][0]["price"]["id"] = "price_other"
        self.event()
        self.assertEqual(effective_plan(1, "premium", self.db, environment=ENV), "free")

    def test_bad_signature_stores_nothing_and_calls_no_provider(self):
        payload, _ = signed_payload("customer.subscription.updated", self.subscription)
        with self.assertRaises(BillingError):
            process_webhook(payload, "bad-signature", self.db, ENV, self.client)
        self.client.v1.subscriptions.retrieve.assert_not_called()

    def test_duplicate_event_is_idempotent(self):
        self.checkout()
        self.assertEqual(self.event(), "processed")
        self.assertEqual(self.event(), "duplicate")
        self.client.v1.subscriptions.retrieve.assert_called_once()

    def test_out_of_order_event_uses_current_stripe_state(self):
        self.paid()
        old = {**self.subscription, "status": "active"}
        self.subscription["status"] = "canceled"
        self.event(obj=old)
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "free")

    def test_payment_failure_revokes_and_recovery_restores(self):
        self.paid()
        self.subscription["status"] = "past_due"
        invoice = {"parent": {"subscription_details": {"subscription": "sub_1"}}}
        self.event("invoice.payment_failed", invoice)
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "free")
        self.subscription["status"] = "active"
        self.event("invoice.paid", invoice, event_id="evt_2")
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "premium")

    def test_cancellation_at_period_end_keeps_paid_access(self):
        self.paid()
        self.subscription["cancel_at_period_end"] = True
        self.event()
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "premium")
        self.assertTrue(billing_account(1, self.db)["cancel_at_period_end"])

    def test_subscription_metadata_and_test_mode_are_checked(self):
        self.checkout()
        self.subscription["metadata"]["immoradar_user_id"] = "2"
        with self.assertRaises(BillingError):
            self.event()
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "free")
        self.subscription["metadata"]["immoradar_user_id"] = "1"
        with self.assertRaises(BillingError):
            self.event(live=True)

    def test_old_cancellation_cannot_revoke_replacement(self):
        self.paid()
        self.subscription["status"] = "canceled"
        self.event()
        self.subscription.update(id="sub_2", status="active")
        self.event(event_id="evt_2")
        replacement = dict(self.subscription)
        self.client.v1.subscriptions.retrieve.return_value = {**replacement, "id": "sub_1", "status": "canceled"}
        self.event(obj={"id": "sub_1"}, event_id="evt_3")
        self.assertEqual(billing_account(1, self.db)["subscription_id"], "sub_2")
        self.assertEqual(effective_plan(1, "free", self.db, environment=ENV), "premium")

    def test_portal_uses_account_customer_not_browser_data(self):
        self.checkout()
        self.assertTrue(create_portal(1, self.db, ENV, self.client).startswith("https://billing.stripe.com/"))
        self.assertEqual(self.client.v1.billing_portal.sessions.create.call_args.args[0]["customer"], "cus_1")
        self.assertEqual(self.client.v1.billing_portal.sessions.create.call_args.args[0]["locale"], "fr-CA")
        with self.assertRaises(BillingError):
            create_portal(2, self.db, ENV, self.client)

    def test_live_launch_does_not_inherit_beta_premium(self):
        self.assertEqual(effective_plan(2, "premium", self.db, environment=ENV), "free")
        self.assertEqual(effective_plan(2, "premium", self.db, environment={}), "premium")
        self.paid()
        self.assertEqual(effective_plan(1, "premium", self.db, environment={**ENV, "IMMORADAR_BILLING_MODE": "live"}), "free")
        with self.assertRaises(BillingError):
            create_portal(1, self.db, {**ENV, "IMMORADAR_BILLING_MODE": "live", "STRIPE_SECRET_KEY": "sk_live_placeholder"}, self.client)

    def test_account_deletion_cannot_orphan_recurring_payment(self):
        self.checkout()
        self.assertFalse(delete_account(1, self.db))
        self.assertTrue(delete_account(2, self.db))
        self.assertIsNotNone(get_user(1, self.db))

    def test_webhook_failure_is_not_recorded_as_success(self):
        self.checkout()
        self.client.v1.subscriptions.retrieve.side_effect = stripe.APIConnectionError("private")
        with self.assertRaises(BillingError):
            self.event()
        with closing(SQLiteRepository(self.db)._connect()) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM billing_events").fetchone()[0], 0)

    def test_refresh_recovers_if_browser_return_is_lost(self):
        self.checkout()
        self.client.v1.subscriptions.list.return_value = {"data": [self.subscription]}
        self.assertTrue(refresh_subscription(1, self.db, ENV, self.client))


if __name__ == "__main__":
    unittest.main()
