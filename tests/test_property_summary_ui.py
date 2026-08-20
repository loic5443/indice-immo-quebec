"""Focused Streamlit assertions for the unified property summary."""

import unittest

from streamlit.testing.v1 import AppTest


class PropertySummaryUiTests(unittest.TestCase):
    def test_summary_prioritizes_known_results_and_keeps_details_secondary(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=3200, other_expenses_monthly=200)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Investisseur locatif')\n"
        ).run(timeout=20)
        text = "\n".join([item.value for item in app.markdown] + [item.value for item in app.caption])
        self.assertIn("Votre synthèse immobilière", text)
        labels = [metric.label for metric in app.metric]
        for label in ("ImmoScore", "Confiance", "Paiement hypothécaire", "Dépenses mensuelles", "Revenus locatifs", "Flux de trésorerie", "Taux de capitalisation", "Rendement sur mise", "Capacité à couvrir la dette (DSCR)"):
            self.assertIn(label, labels)
        self.assertIn("Modifier les hypothèses", [button.label for button in app.button])
        self.assertIn("Voir les alertes Premium", [button.label for button in app.button])
        self.assertTrue(any(item.label == "ImmoValue" for item in app.tabs))
        self.assertTrue(any(item.label == "Vérifications détaillées" for item in app.tabs))

    def test_non_rental_summary_does_not_present_zero_as_a_return(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
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


if __name__ == "__main__":
    unittest.main()
