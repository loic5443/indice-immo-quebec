"""Focused presentation checks for the product privacy page."""

import unittest

from streamlit.testing.v1 import AppTest


class PrivacyUiTests(unittest.TestCase):
    def test_privacy_page_explains_controls_without_claiming_external_sharing(self):
        app = AppTest.from_string("import components.privacy as page\npage.show_privacy()").run(timeout=20)
        self.assertFalse(app.exception)
        text = " ".join(item.value for item in app.markdown) + " ".join(item.value for item in app.caption)
        self.assertIn("Vos données servent votre dossier", text)
        self.assertIn("seulement après votre consentement", text)
        self.assertIn("ne sont pas envoyés aux mesures", text)
        self.assertIn("aucun paiement réel", text)
        labels = [button.label for button in app.button]
        self.assertIn("Gérer mes données", labels)
        self.assertIn("Analyser une propriété", labels)


if __name__ == "__main__":
    unittest.main()
