"""Streamlit regressions for public navigation, selections and calculation gating."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data.database import create_user, initialize_database
from services.municipal_comparison_service import import_profile


HEADER = "an_edition,an_donnee,cod_geo,nom_organisme,desi_org,cod_mrc,nom_mrc,cod_cm,nom_cm,cod_ra,nom_ra,type_org,population,cod_cp,desc_cp,FIALX01959,FIALX01960,FIALX01961,FIALX01962,FIALX01963,FIALX01977,FIALX02005,FIALX02006,FIALX02007,FIALX02008,FIALX02009,FIALX02010,FIALX02011,FIALX02097\n"


def _row(code, municipality):
    return f"2024,2025,{code},{municipality},M,,,,,1,R,Municipalité locale,100,CP1,a,1000,1,1,1,1,1,1,1,1,1,10,2,3,4\n"


class PublicUiRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "ui.sqlite"
        initialize_database(self.db)
        create_user("Admin", "admin@example.com", "Motdepasse1", self.db)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE users SET role='admin' WHERE id=1")
        import_profile(1, self.db, (HEADER + _row("66023", "Montréal") + _row("23027", "Québec")).encode())

    def tearDown(self):
        self.tmp.cleanup()

    def _component(self, module, function):
        return AppTest.from_string(
            "from pathlib import Path\n"
            f"import {module} as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            f"page.{function}()\n"
        )

    @staticmethod
    def _button(app, label):
        return next(button for button in app.button if button.label == label)

    def test_markets_search_does_not_remove_existing_selection(self):
        app = self._component("components.markets", "show_markets")
        app.run(timeout=20)
        app.multiselect(key="municipal_selected").set_value(["Montréal"]).run(timeout=20)
        app.text_input(key="municipal_search").set_value("Québec").run(timeout=20)
        self.assertEqual(app.multiselect(key="municipal_selected").value, ["Montréal"])
        app.multiselect(key="municipal_selected").set_value(["Montréal", "Québec"]).run(timeout=20)
        self.assertEqual(app.multiselect(key="municipal_selected").value, ["Montréal", "Québec"])
        self._button(app, "Réinitialiser la comparaison").click().run(timeout=20)
        self.assertEqual(app.multiselect(key="municipal_selected").value, [])
        self.assertEqual(list(app.exception), [])

    def test_analysis_gates_results_and_keeps_step_labels_consistent(self):
        app = self._component("components.property_analysis", "show_property_analysis")
        app.run(timeout=20)
        self.assertEqual(list(app.metric), [])
        self.assertTrue(any("Aucune analyse personnelle" in item.value for item in app.info))
        app.selectbox(key="workflow_objective_choice").set_value("Investir et louer")
        self._button(app, "Suivant").click().run(timeout=20)
        self.assertEqual(app.selectbox(key="analysis_step_selector").value, 2)
        app.text_input(key="workflow_property_name").set_value("Duplex")
        app.selectbox(key="workflow_property_type").set_value("Duplex")
        self._button(app, "Suivant").click().run(timeout=20)
        self.assertEqual(app.selectbox(key="analysis_step_selector").value, 3)
        app.number_input(key="property_price").set_value(500000)
        app.number_input(key="down_payment").set_value(100000)
        self._button(app, "Suivant").click().run(timeout=20)
        for expected_step in range(4, 10):
            self.assertEqual(app.selectbox(key="analysis_step_selector").value, expected_step)
            if expected_step < 9:
                self._button(app, "Suivant").click().run(timeout=20)
        app.selectbox(key="analysis_step_selector").set_value(2).run(timeout=20)
        self.assertEqual(app.selectbox(key="analysis_step_selector").value, 2)
        app.button(key="calculate_analysis").click().run(timeout=20)
        self.assertGreater(len(app.metric), 0)
        self.assertEqual(list(app.exception), [])

    def test_home_has_one_premium_alert_section_and_feedback_has_a_sign_in_path(self):
        home = self._component("components.home", "show_home")
        home.run(timeout=20)
        self.assertEqual(sum("Gardez une longueur" in item.value for item in home.get("markdown")), 1)
        self.assertTrue(any("repère fiscal" in item.value and "pas un prix de vente" in item.value for item in home.caption))
        feedback = AppTest.from_string(
            "import components.feedback as page\n"
            "original_is_authenticated = page.is_authenticated\n"
            "try:\n"
            "    page.is_authenticated = lambda: False\n"
            "    page.show_feedback()\n"
            "finally:\n"
            "    page.is_authenticated = original_is_authenticated\n"
        )
        feedback.run(timeout=20)
        self.assertEqual(sum(item.label == "Accéder à Mon compte" for item in feedback.button), 1)

    def test_empty_login_shows_required_fields_without_changing_invalid_login_message(self):
        account = AppTest.from_string(
            "import components.account as page\n"
            "original_authenticated, original_authenticate = page.is_authenticated, page.authenticate_user\n"
            "try:\n"
            "    page.is_authenticated = lambda: False\n"
            "    page.authenticate_user = lambda email, password: None\n"
            "    page.show_account()\n"
            "finally:\n"
            "    page.is_authenticated, page.authenticate_user = original_authenticated, original_authenticate\n"
        )
        account.run(timeout=20)
        self._button(account, "Se connecter").click().run(timeout=20)
        errors = [item.value for item in account.error]
        self.assertIn("Le courriel est requis.", errors)
        self.assertIn("Le mot de passe est requis.", errors)
        account.text_input(key="login_email").set_value("personne@example.com")
        account.text_input(key="login_password").set_value("incorrect")
        self._button(account, "Se connecter").click().run(timeout=20)
        self.assertIn("Adresse courriel ou mot de passe incorrect.", [item.value for item in account.error])
