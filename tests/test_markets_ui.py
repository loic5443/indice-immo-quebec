"""Presentation checks for honest municipal-market availability states."""

import unittest

from streamlit.testing.v1 import AppTest


class MarketsUiTests(unittest.TestCase):
    def test_empty_source_explains_that_no_official_data_is_loaded(self):
        app = AppTest.from_string(
            "import components.markets as page\n"
            "original_municipalities = page.municipalities\n"
            "try:\n"
            "    page.municipalities = lambda *_args: []\n"
            "    page.show_markets()\n"
            "finally:\n"
            "    page.municipalities = original_municipalities\n"
        ).run(timeout=20)
        self.assertTrue(any("Aucune donnée municipale officielle" in item.value for item in app.warning))
        self.assertEqual(list(app.multiselect), [])

    def test_loaded_source_shows_counts_without_invented_market_indicators(self):
        app = AppTest.from_string(
            "import components.markets as page\n"
            "original_municipalities, original_comparison = page.municipalities, page.comparison\n"
            "try:\n"
            "    page.municipalities = lambda _database, _query='': ['Montréal', 'Québec']\n"
            "    page.comparison = lambda *_args: {'available': False, 'year': None, 'rows': []}\n"
            "    page.show_markets()\n"
            "finally:\n"
            "    page.municipalities, page.comparison = original_municipalities, original_comparison\n"
        ).run(timeout=20)
        self.assertIn("Municipalités disponibles", [metric.label for metric in app.metric])
        self.assertIn("Rechercher et ajouter une municipalité", [item.label for item in app.text_input])
        text = " ".join(item.value for item in app.info)
        self.assertIn("ne sont pas des prix de vente", text)


if __name__ == "__main__":
    unittest.main()
