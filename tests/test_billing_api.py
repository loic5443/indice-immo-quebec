"""HTTP webhook contract: authenticate, bound buffering and retry failures."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from services.billing_api import app
from services.billing_service import BillingError


class BillingApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_exposes_no_configuration(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_invalid_signature_is_rejected(self):
        with patch("services.billing_api.process_webhook", side_effect=BillingError("Signature de paiement invalide.")):
            response = self.client.post("/stripe/webhook", content=b"{}", headers={"stripe-signature": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "invalid_event"})

    def test_provider_failure_requests_stripe_retry_without_details(self):
        with patch("services.billing_api.process_webhook", side_effect=BillingError("private detail")):
            response = self.client.post("/stripe/webhook", content=b"{}")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)

    def test_large_payload_is_rejected_before_processing(self):
        with patch("services.billing_api.process_webhook") as processor:
            response = self.client.post("/stripe/webhook", content=b"x" * 1_000_001)
        self.assertEqual(response.status_code, 413)
        processor.assert_not_called()

    def test_signed_processed_events_are_acknowledged(self):
        with patch("services.billing_api.process_webhook", return_value="processed") as processor:
            response = self.client.post("/stripe/webhook", content=b"{}", headers={"stripe-signature": "signature"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "processed"})
        self.assertEqual(processor.call_args.args[:2], (b"{}", "signature"))
