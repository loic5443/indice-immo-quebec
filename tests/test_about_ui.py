"""Trust and navigation regressions for the secondary About page."""

import unittest

from streamlit.testing.v1 import AppTest


class AboutUiTests(unittest.TestCase):
    def test_about_separates_official_value_financial_analysis_and_immovalue(self):
        app = AppTest.from_string("import components.about as page\npage.show_about()").run(timeout=20)
        self.assertFalse(app.exception)
        text = " ".join(item.value for item in app.markdown) + " ".join(item.value for item in app.caption)
        self.assertIn("Valeur municipale officielle", text)
        self.assertIn("Votre analyse financière", text)
        self.assertIn("ImmoValue expérimental", text)
        self.assertIn("ne produit pas une évaluation officielle", text)
        self.assertIn("ne sont pas envoyés à la télémétrie", text)
        self.assertIn("Analyser une propriété", [button.label for button in app.button])
        self.assertIn("Découvrir Premium", [button.label for button in app.button])


if __name__ == "__main__":
    unittest.main()
