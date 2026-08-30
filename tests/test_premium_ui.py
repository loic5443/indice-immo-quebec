"""Focused presentation tests for the Premium conversion page."""

import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database
from components.premium import _free_estimation_limit


class PremiumUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "premium-ui.sqlite"
        initialize_database(self.database_path)
        created, _ = create_user("Compte bêta", "premium-ui@example.test", "motdepasse-solide", self.database_path)
        self.assertTrue(created)
        self.user = authenticate_user("premium-ui@example.test", "motdepasse-solide", self.database_path)

    def tearDown(self):
        self.temp.cleanup()

    def _app(self, authenticated: bool, plan: str = "free"):
        from streamlit.testing.v1 import AppTest

        source = f'''
import components.premium as page
page.DATABASE_PATH = r"{self.database_path}"
page.is_authenticated = lambda: {authenticated}
page.current_user = lambda: {{"id": {self.user["id"]}, "plan": "{plan}", "role": "user"}}
page.show_premium()
'''
        return AppTest.from_string(source).run(timeout=20)

    def test_guest_sees_concrete_offer_and_local_account_path(self):
        app = self._app(False)
        self.assertFalse(app.exception)
        text = " ".join(item.value for item in app.markdown) + " ".join(item.value for item in app.info)
        self.assertIn("Le dossier ne s’arrête pas au premier calcul", text)
        self.assertIn("Aucun paiement n’est demandé", text)
        self.assertIn("Créer mon espace pour être averti", [button.label for button in app.button])

    def test_premium_beta_account_sees_its_current_access(self):
        app = self._app(True, "premium")
        self.assertFalse(app.exception)
        self.assertTrue(any("accès Premium bêta est actif" in item.value for item in app.success))
        self.assertIn("Enregistrer mon choix", [button.label for button in app.button])

    def test_preparation_column_does_not_claim_a_ready_feature(self):
        app = self._app(False)
        markdown = "\n".join(item.value for item in app.markdown)
        preparation = markdown.split("En préparation", 1)[1].split("Ce qui se débloque réellement", 1)[0]
        self.assertNotIn("data-pill real'>Disponible</span>", preparation)
        self.assertEqual(preparation.count("Bientôt disponible"), 2)

    def test_free_quota_copy_matches_the_current_beta_setting(self):
        beta_title, beta_table = _free_estimation_limit(False)
        enforced_title, enforced_table = _free_estimation_limit(True)
        self.assertIn("désactivé pendant la bêta", beta_title)
        self.assertIn("désactivé", beta_table)
        self.assertIn("par mois", enforced_title)
        self.assertIn("1 complète", enforced_table)


if __name__ == "__main__":
    unittest.main()
