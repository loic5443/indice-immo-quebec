"""Focused Streamlit regression for the guided ImmoValue flow."""

import unittest

from streamlit.testing.v1 import AppTest


class GuidedImmoValueUiTests(unittest.TestCase):
    def _app(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_immovalue()\n"
        )
        return app.run(timeout=20)

    @staticmethod
    def _add(app, number: int, price: float):
        app.text_input(key="iv_add_address").set_value(f"Comparable fictif {number}")
        app.number_input(key="iv_add_price").set_value(price)
        app.selectbox(key="iv_add_type").set_value("Maison")
        app.number_input(key="iv_add_area").set_value(100.0)
        app.text_input(key="iv_add_city").set_value("Ville de test")
        app.text_input(key="iv_add_source").set_value("Donnée de test autorisée")
        app.checkbox(key="iv_add_closed").set_value(True)
        app.checkbox(key="iv_add_rights").set_value(True)
        next(button for button in app.button if button.label == "Ajouter ce comparable").click().run(timeout=20)

    def test_three_guided_comparables_produce_an_explicit_result_only_after_click(self):
        app = self._app()
        app.text_input(key="iv_name").set_value("Sujet fictif")
        app.selectbox(key="iv_type").set_value("Maison")
        app.number_input(key="iv_area").set_value(100.0)
        app.number_input(key="iv_asking").set_value(600_000.0)
        self._add(app, 1, 500_000.0)
        self._add(app, 2, 510_000.0)
        self._add(app, 3, 520_000.0)
        self.assertNotIn("Valeur expérimentale", [metric.label for metric in app.metric])
        app.button(key="generate_immovalue").click().run(timeout=20)
        labels = [metric.label for metric in app.metric]
        self.assertIn("Valeur expérimentale", labels)
        self.assertIn("Valeur au rôle", labels)
        self.assertIn("Prix saisi", labels)
        self.assertTrue(any("prix demandé" in item.value.casefold() for item in app.info))
        self.assertTrue(any("Pourquoi cette estimation" in item.label for item in app.expander))

    def test_guided_comparable_can_be_opened_for_edit_then_removed_before_calculation(self):
        app = self._app()
        self._add(app, 1, 500_000.0)
        app.button(key="iv_edit_0").click().run(timeout=20)
        self.assertTrue(any(button.label == "Enregistrer les modifications" for button in app.button))
        app.button(key="iv_delete_0").click().run(timeout=20)
        app.run(timeout=20)
        self.assertFalse(any(button.key == "iv_delete_0" for button in app.button))
        self.assertNotIn("Produire l’estimation ImmoValue", [button.label for button in app.button])


if __name__ == "__main__":
    unittest.main()
