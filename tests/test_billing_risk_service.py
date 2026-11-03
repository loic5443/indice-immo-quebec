from contextlib import closing
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import stripe

from repositories.sqlite_repository import SQLiteRepository
from services.billing_risk_service import open_reviews, resolve_review
from services.billing_service import BillingError
from tests.test_billing_service import BillingTests


class BillingRiskTests(unittest.TestCase):
    def setUp(self):
        self.fixture = BillingTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.checkout()
        self.client = self.fixture.client
        self.charge = {"id": "ch_risk", "livemode": False, "payment_intent": "pi_risk"}
        self.client.v1.charges = SimpleNamespace(retrieve=Mock(side_effect=lambda *_: self.charge))
        self.client.v1.invoice_payments = SimpleNamespace(list=Mock(return_value={"data": [{"invoice": "in_risk"}], "has_more": False}))
        self.client.v1.invoices = SimpleNamespace(retrieve=Mock(return_value={"id": "in_risk", "livemode": False,
            "parent": {"subscription_details": {"subscription": "sub_1"}}}))

    def event(self, kind="charge.refunded", event_id="evt_risk"):
        obj = {"id": "ch_risk"} if kind == "charge.refunded" else {"id": "risk_object", "charge": "ch_risk"}
        return self.fixture.event(kind=kind, obj=obj, event_id=event_id)

    def rows(self, table):
        with closing(SQLiteRepository(self.fixture.db)._connect()) as connection:
            return connection.execute("SELECT * FROM " + table).fetchall()

    def test_each_risk_event_maps_invoice_graph_to_owned_subscription_and_deduplicates(self):
        for n, kind in enumerate(("charge.refunded", "charge.dispute.created", "radar.early_fraud_warning.created")):
            self.assertEqual(self.event(kind, f"evt_{n}"), "processed")
            self.assertEqual(self.event(kind, f"evt_{n}"), "duplicate")
        self.assertEqual(len(self.rows("billing_risk_reviews")), 3)
        self.assertEqual(self.client.v1.charges.retrieve.call_count, 3)
        self.client.v1.invoice_payments.list.assert_called_with({
            "payment": {"type": "payment_intent", "payment_intent": "pi_risk"}, "limit": 100})
        self.assertEqual({r["subscription_id"] for r in self.rows("billing_risk_reviews")}, {"sub_1"})

    def test_legacy_invoice_reference_is_supported_without_metadata_fallback(self):
        self.charge["invoice"] = "in_risk"
        self.assertEqual(self.event(), "processed")
        self.client.v1.invoice_payments.list.assert_not_called()
        self.assertEqual(len(self.rows("billing_risk_reviews")), 1)

    def test_wrong_mode_and_provider_failure_are_retryable_without_acknowledgement(self):
        self.charge["livemode"] = True
        with self.assertRaises(BillingError):
            self.event()
        self.charge["livemode"] = False
        self.client.v1.invoices.retrieve.side_effect = stripe.APIConnectionError("private provider detail")
        with self.assertRaises(BillingError):
            self.event()
        self.assertEqual(self.rows("billing_events"), [])
        self.assertEqual(self.rows("billing_risk_reviews"), [])

    def test_unowned_and_non_subscription_payments_do_not_create_review_cases(self):
        self.fixture.subscription["customer"] = "cus_unrelated"
        self.event(event_id="evt_other")
        self.client.v1.invoice_payments.list.return_value = {"data": [], "has_more": False}
        self.event(event_id="evt_oneoff")
        self.assertEqual(self.rows("billing_risk_reviews"), [])

    def test_truncated_graph_is_retried_instead_of_silently_ignored(self):
        self.client.v1.invoice_payments.list.return_value["has_more"] = True
        with self.assertRaises(BillingError):
            self.event()
        self.assertEqual(self.rows("billing_events"), [])

    def test_only_real_admin_can_view_and_close_review_and_closure_is_audited(self):
        self.event()
        for operation in (lambda: open_reviews(1, self.fixture.db),
                          lambda: resolve_review(1, self.fixture.db, "evt_risk", "sub_1")):
            with self.assertRaises(PermissionError):
                operation()
        with sqlite3.connect(self.fixture.db) as connection:
            connection.execute("UPDATE users SET role='admin' WHERE id=2")
        self.assertEqual(len(open_reviews(2, self.fixture.db)), 1)
        resolve_review(2, self.fixture.db, "evt_risk", "sub_1")
        self.assertEqual(open_reviews(2, self.fixture.db), [])
        self.assertEqual(len(self.rows("admin_audit_log")), 1)
