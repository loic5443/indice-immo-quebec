"""Commercial UI journey and recovery after a payment return."""
import tempfile
import unittest
from pathlib import Path
from data.database import initialize_database, create_user


class BillingUiTests(unittest.TestCase):
    def setUp(self):
        import components.premium as premium
        import components.billing as billing
        self.original_offer = premium.available_offer
        self.original_checkout = billing.create_checkout
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "ui.sqlite"
        initialize_database(self.db)
        create_user("Acheteur", "buyer@example.test", "long-password-test", self.db)

    def tearDown(self):
        import components.premium as premium
        import components.billing as billing
        premium.available_offer = self.original_offer
        billing.create_checkout = self.original_checkout
        self.temp.cleanup()

    def app(self, authenticated=True):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_string(f'''
import components.premium as page
import components.billing as billing
page.DATABASE_PATH = r"{self.db}"
page.is_authenticated = lambda: {authenticated}
page.current_user = lambda: {{"id": 1, "plan": "free", "role": "user"}}
page.available_offer = lambda: ({{"price_label": "29,00 $ CA / mois", "mode": "live", "tax_inclusive": False}}, None)
billing.create_checkout = lambda *_args: "https://checkout.stripe.com/c/pay/test"
page.show_premium()
''').run(timeout=20)

    def test_offer_shows_price_and_checkout_instead_of_waitlist(self):
        app = self.app()
        self.assertFalse(app.exception)
        markup = " ".join(item.value for item in app.markdown)
        self.assertIn("29,00 $ CA / mois", markup)
        self.assertNotIn("Tarif à confirmer", markup)
        labels = [button.label for button in app.button]
        self.assertIn("Choisir Premium", labels)
        self.assertNotIn("Enregistrer mon choix", labels)
        app.button(key="billing_checkout").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["billing_checkout_owner"], 1)
        self.assertIn("checkout.stripe.com", app.session_state["billing_checkout_url"])

    def test_guest_creates_account_before_payment(self):
        app = self.app(False)
        self.assertFalse(app.exception)
        self.assertIn("Créer mon compte pour choisir Premium", [button.label for button in app.button])
        self.assertNotIn("Choisir Premium", [button.label for button in app.button])
        app.session_state["return_to_analysis_after_auth"] = True
        app.button(key="billing_signup").click().run(timeout=20)
        self.assertEqual(app.session_state["main_navigation"], "Mon compte")
        self.assertTrue(app.session_state["return_to_premium_after_auth"])
        self.assertNotIn("return_to_analysis_after_auth", app.session_state)

    def test_guest_payment_return_can_navigate_to_login(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_string(f'''
import components.billing as billing
billing.handle_billing_return(None, r"{self.db}")
''')
        app.query_params["billing"] = "success"
        app.query_params["session_id"] = "cs_test_return"
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["pending_billing_return"]["session_id"], "cs_test_return")
        self.assertNotIn("billing", app.query_params)
        app.button(key="billing_return_login").click().run(timeout=20)
        self.assertEqual(app.session_state["main_navigation"], "Mon compte")

    def test_configuration_failure_is_visible_without_payment_button(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_string(f'''
import components.premium as page
page.DATABASE_PATH = r"{self.db}"
page.is_authenticated = lambda: False
page.available_offer = lambda: (None, "Configuration indisponible.")
page.show_premium()
''').run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Configuration indisponible" in item.value for item in app.error))
        self.assertNotIn("Choisir Premium", [button.label for button in app.button])
