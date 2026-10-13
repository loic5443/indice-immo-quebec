import unittest
from streamlit.testing.v1 import AppTest


class GuestQuotaTests(unittest.TestCase):
    def test_guest_needs_account_when_commercial_quota_is_enforced(self):
        app = AppTest.from_string('''
from unittest.mock import patch
import components.property_analysis as page
with patch.object(page,"is_authenticated",lambda:False), patch.object(page,"quota_is_enforced",lambda _path:True):
    page._show_immovalue()
''').run(timeout=20)
        app.text_input(key="iv_name").set_value("Sujet fictif")
        app.selectbox(key="iv_type").set_value("Maison")
        app.number_input(key="iv_area").set_value(100.0)
        for number in range(3):
            app.text_input(key="iv_add_address").set_value(f"Comparable fictif {number}")
            app.number_input(key="iv_add_price").set_value(500000.0 + 10000 * number)
            app.selectbox(key="iv_add_type").set_value("Maison")
            app.number_input(key="iv_add_area").set_value(100.0)
            app.text_input(key="iv_add_city").set_value("Ville de test")
            app.text_input(key="iv_add_source").set_value("Test autorisé")
            app.checkbox(key="iv_add_closed").set_value(True)
            app.checkbox(key="iv_add_rights").set_value(True)
            next(button for button in app.button if button.label=="Ajouter ce comparable").click().run(timeout=20)
        app.button(key="generate_immovalue").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertNotIn("Valeur expérimentale", [metric.label for metric in app.metric])
        app.button(key="iv_quota_account").click().run(timeout=20)
        self.assertTrue(app.session_state["return_to_analysis_after_auth"])
        self.assertEqual(app.session_state["main_navigation"], "Mon compte")
        self.assertEqual(len(app.session_state["iv_manual_comparables"]), 3)
