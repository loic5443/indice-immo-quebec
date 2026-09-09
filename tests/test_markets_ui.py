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
        self.assertTrue(any("comparaison municipale officielle" in item.value for item in app.warning))
        self.assertEqual(list(app.multiselect), [])
        self.assertIn("Analyser une propriété", [button.label for button in app.button])
        text = " ".join(item.value for item in app.warning)
        self.assertIn("ne crée aucun indicateur de marché", text)

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
        self.assertIn("Commencez par rechercher une municipalité", text)
        self.assertTrue(any("ne retire jamais les municipalités" in item.value for item in app.caption))

    def test_one_selected_municipality_gives_a_clear_next_step(self):
        app = AppTest.from_string(
            "import components.markets as page\n"
            "original_municipalities, original_comparison = page.municipalities, page.comparison\n"
            "try:\n"
            "    page.municipalities = lambda _database, _query='': ['Montréal', 'Québec']\n"
            "    page.comparison = lambda *_args: {'available': False, 'year': None, 'rows': [], 'missing': []}\n"
            "    page.show_markets()\n"
            "finally:\n"
            "    page.municipalities, page.comparison = original_municipalities, original_comparison\n"
        ).run(timeout=20)
        app.multiselect(key="municipal_selected").set_value(["Montréal"]).run(timeout=20)
        self.assertTrue(any("Montréal est sélectionnée" in item.value for item in app.info))

    def test_available_comparison_has_one_official_indicator_selector(self):
        rows = [
            {"indicator_code": code, "municipality_name": municipality, "value": value, "year": 2025}
            for municipality, multiplier in (("Montréal", 2), ("Québec", 1))
            for code, value in (
                ("population", 100 * multiplier),
                ("uniformized_residential_assessment_average", 200_000 * multiplier),
                ("uniformized_property_wealth", 300_000 * multiplier),
                ("uniformized_property_wealth_per_unit", 400_000 * multiplier),
            )
        ]
        app = AppTest.from_string(
            "import components.markets as page\n"
            "original_municipalities, original_comparison = page.municipalities, page.comparison\n"
            "try:\n"
            "    page.municipalities = lambda _database, _query='': ['Montréal', 'Québec']\n"
            f"    page.comparison = lambda *_args: {{'available': True, 'year': 2025, 'rows': {rows!r}, 'missing': []}}\n"
            "    page.show_markets()\n"
            "finally:\n"
            "    page.municipalities, page.comparison = original_municipalities, original_comparison\n"
        ).run(timeout=20)
        app.multiselect(key="municipal_selected").set_value(["Montréal", "Québec"]).run(timeout=20)
        self.assertEqual(app.selectbox(key="municipal_indicator_view").value, "population")
        self.assertTrue(any("Visualisation des données officielles" in item.value for item in app.caption))
        self.assertEqual(list(app.exception), [])


if __name__ == "__main__":
    unittest.main()
