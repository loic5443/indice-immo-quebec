import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.billing_api import app
from services.legal_pages import legal_document


class PublicLegalPagesTests(unittest.TestCase):
    def test_public_documents_are_printable_without_an_account_or_secret_values(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "private-key-never-publish", "IMMORADAR_BILLING_ENABLED": "0"}):
            client = TestClient(app)
            for path in ("/conditions", "/confidentialite"):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])
                self.assertIn('lang="fr-CA"', response.text)
                self.assertIn("loicstpierre29@gmail.com", response.text)
                self.assertNotIn("private-key-never-publish", response.text)
            self.assertIn("ne sont pas encore ouverts", client.get("/conditions").text)

    def test_operator_coordinates_are_escaped_in_public_html(self):
        document = legal_document("conditions", {"CENLIO_BUSINESS_ADDRESS": '<script>alert("x")</script>',
                                                 "CENLIO_BUSINESS_PHONE": "555 & 000"})
        self.assertNotIn("<script>", document)
        self.assertIn("&lt;script&gt;", document)
        self.assertIn("555 &amp; 000", document)
