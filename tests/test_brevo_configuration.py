"""Safe, no-send checks for the optional Brevo configuration probe."""

import unittest
from urllib.error import HTTPError

from providers.brevo_email import verify_delivery_configuration


ENVIRONMENT = {
    "IMMORADAR_ALERT_DELIVERY_ENABLED": "true",
    "BREVO_API_KEY": "test-key",
    "BREVO_SENDER_EMAIL": "sender@example.test",
}


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class BrevoConfigurationTests(unittest.TestCase):
    def test_verified_configuration_calls_only_the_account_endpoint(self):
        requests = []

        def opener(request, timeout):
            requests.append((request.full_url, timeout))
            return _Response()

        self.assertEqual(verify_delivery_configuration(ENVIRONMENT, opener=opener), "verified")
        self.assertEqual(requests, [("https://api.brevo.com/v3/account", 10)])

    def test_rejected_key_is_categorical_and_never_exposes_credentials(self):
        def rejected(request, timeout):
            raise HTTPError(request.full_url, 401, "rejected", {}, None)

        self.assertEqual(verify_delivery_configuration(ENVIRONMENT, opener=rejected), "credentials_rejected")

    def test_disabled_delivery_never_calls_the_network(self):
        self.assertEqual(
            verify_delivery_configuration({}, opener=lambda *_args: self.fail("network should not run")),
            "disabled",
        )


if __name__ == "__main__":
    unittest.main()
