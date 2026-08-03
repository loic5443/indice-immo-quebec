"""Regression checks for the five-destination product structure and dossier messaging."""

import unittest
from pathlib import Path

from components.sidebar import PAGE_ALIASES, PRIMARY_PAGES


class ProductStructureTests(unittest.TestCase):
    def test_primary_navigation_is_limited_to_the_five_product_destinations(self):
        self.assertEqual(PRIMARY_PAGES, ["Accueil", "Analyser", "Mes propriétés", "Marché", "Premium"])
        self.assertEqual(PAGE_ALIASES["Analyse immobilière"], "Analyser")
        self.assertEqual(PAGE_ALIASES["Mes analyses"], "Mes propriétés")

    def test_sidebar_keeps_secondary_destinations_out_of_primary_radio(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string("import components.sidebar as page\npage.show_sidebar()").run(timeout=20)
        self.assertEqual(app.radio(key="primary_navigation").options, PRIMARY_PAGES)
        app.radio(key="primary_navigation").set_value("Analyser").run(timeout=20)
        self.assertEqual(app.session_state["main_navigation"], "Analyser")

    def test_dossier_keeps_municipal_role_distinct_from_market_value(self):
        source = (Path("components") / "property_analysis.py").read_text(encoding="utf-8")
        self.assertIn("Valeur au rôle — ce n’est pas une valeur marchande", source)
        self.assertIn("Vue d’ensemble", source)
        self.assertIn("Risques et vérifications", source)

    def test_alerts_are_never_presented_as_active_for_a_free_account(self):
        source = (Path("components") / "alerts.py").read_text(encoding="utf-8")
        self.assertIn("APERÇU PREMIUM VERROUILLÉ", source)
        self.assertIn("Aucune alerte calculable", source)
        self.assertNotIn("send_email", source)

    def test_dynamic_page_titles_do_not_reuse_the_home_heading_anchor(self):
        for filename in ("home.py", "premium.py", "account.py", "saved_analyses.py", "markets.py"):
            source = (Path("components") / filename).read_text(encoding="utf-8")
            self.assertNotIn("#reveler-la-valeur-et-analyser-votre-projet", source)
        self.assertIn("hero-title", (Path("components") / "home.py").read_text(encoding="utf-8"))
        self.assertIn("st.title", (Path("components") / "account.py").read_text(encoding="utf-8"))
