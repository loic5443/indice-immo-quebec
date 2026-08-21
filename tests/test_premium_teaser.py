"""Focused tests for contextual, truthful Premium invitations."""

import unittest


class PremiumTeaserTests(unittest.TestCase):
    def test_teaser_names_the_locked_outcome_and_keeps_beta_pricing_clear(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string('''
from components.premium_teaser import show_premium_teaser
show_premium_teaser(
    feature="Rapport PDF complet",
    title="Gardez une lecture complète.",
    detail="Le rapport reprend seulement les données déjà sauvegardées.",
    key="test_premium_teaser",
)
''').run(timeout=20)
        self.assertFalse(app.exception)
        text = " ".join(item.value for item in app.markdown)
        self.assertIn("Rapport PDF complet", text)
        self.assertIn("Aucun paiement n’est demandé", text)
        self.assertIn("Découvrir Premium", [button.label for button in app.button])


if __name__ == "__main__":
    unittest.main()
