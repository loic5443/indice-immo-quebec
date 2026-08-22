"""Focused Streamlit assertions for the unified property summary."""

import unittest

from streamlit.testing.v1 import AppTest


class PropertySummaryUiTests(unittest.TestCase):
    def test_summary_prioritizes_known_results_and_keeps_details_secondary(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "page.is_authenticated = lambda: False\n"
            "inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=3200, other_expenses_monthly=200)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Investisseur locatif')\n"
        ).run(timeout=20)
        text = "\n".join([item.value for item in app.markdown] + [item.value for item in app.caption])
        self.assertIn("Votre synthèse immobilière", text)
        labels = [metric.label for metric in app.metric]
        for label in ("ImmoScore", "Confiance", "Paiement hypothécaire", "Dépenses mensuelles", "Revenus locatifs", "Flux de trésorerie", "Taux de capitalisation", "Rendement sur mise", "Capacité à couvrir la dette (DSCR)"):
            self.assertIn(label, labels)
        buttons = [button.label for button in app.button]
        self.assertIn("Créer mon espace gratuit", buttons)
        self.assertIn("Modifier mes chiffres", buttons)
        self.assertIn("Découvrir Premium", buttons)
        self.assertEqual(
            [item.label for item in app.tabs],
            ["Vue d’ensemble", "Finances", "Risques et vérifications", "Détails et sources"],
        )

    def test_authenticated_summary_makes_saving_the_clear_primary_action(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "page.is_authenticated = lambda: True\n"
            "page.current_user = lambda: {'id': 1, 'plan': 'free', 'role': 'user'}\n"
            "page.quota_status = lambda *_args: {'label': '1 estimation complète restante ce mois-ci'}\n"
            "page.quota_is_enforced = lambda *_args: False\n"
            "inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=3200, other_expenses_monthly=200)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Investisseur locatif')\n"
        ).run(timeout=20)
        buttons = [button.label for button in app.button]
        self.assertIn("Sauvegarder mon dossier", buttons)
        self.assertIn("Découvrir le suivi Premium", buttons)
        self.assertIn("Modifier mes chiffres", buttons)

    def test_non_rental_summary_does_not_present_zero_as_a_return(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "page.is_authenticated = lambda: False\n"
            "inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=0, other_expenses_monthly=0)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Premier acheteur')\n"
        ).run(timeout=20)
        values = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(values["Revenus locatifs"], "Non applicable")
        self.assertEqual(values["Flux de trésorerie"], "Non applicable")

    def test_value_comparison_explains_the_fiscal_role_limit(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_summary_value_cards(None, None)\n"
        ).run(timeout=20)
        notices = "\n".join(item.value for item in app.info)
        self.assertIn("repère fiscal officiel", notices)
        self.assertIn("plus élevée ou plus basse", notices)
        self.assertIn("secteur", notices)

    def test_property_stage_collects_an_optional_asking_price_before_finances(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_property_stage()\n"
        ).run(timeout=20)
        asking = app.number_input(key="iv_asking")
        self.assertEqual(asking.label, "Prix demandé (facultatif)")
        asking.set_value(575_000.0).run(timeout=20)
        self.assertEqual(app.number_input(key="iv_asking").value, 575_000.0)
        captions = "\n".join(item.value for item in app.caption)
        self.assertIn("Il ne remplace pas le prix retenu", captions)

    def test_financial_price_is_labeled_as_a_separate_assumption(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_finance_stage()\n"
        ).run(timeout=20)
        self.assertEqual(app.number_input(key="property_price").label, "Prix retenu pour vos calculs ($)")
        captions = "\n".join(item.value for item in app.caption)
        self.assertIn("reste distinct du rôle municipal et d’ImmoValue", captions)

    def test_renewal_date_is_optional_in_advanced_financial_inputs(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_finance_stage()\n"
        ).run(timeout=20)
        self.assertEqual(app.date_input(key="mortgage_renewal_date").label, "Date de renouvellement hypothécaire (facultatif)")


if __name__ == "__main__":
    unittest.main()
