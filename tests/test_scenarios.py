"""Deterministic scenario and resilience tests."""

import unittest

from calculations.real_estate import PropertyInputs
from domain.scenarios import build_resilience_tests, build_standard_scenarios


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.inputs = PropertyInputs(
            price=500_000, down_payment=125_000, annual_interest_rate=5.0, amortization_years=25,
            municipal_taxes_annual=3_600, school_taxes_annual=400, insurance_monthly=100,
            condo_fees_monthly=0, rental_income_monthly=3_600, other_expenses_monthly=200,
            vacancy_rate_pct=3, maintenance_monthly=100, capital_reserve_monthly=100,
        )

    def test_standard_scenarios_are_present_and_deterministic(self):
        first = build_standard_scenarios(self.inputs, "Investisseur locatif")
        second = build_standard_scenarios(self.inputs, "Investisseur locatif")
        self.assertEqual(first, second)
        self.assertEqual([item.name for item in first], ["Prudent", "Scénario de base", "Favorable"])
        self.assertLess(first[0].financial.cash_flow_monthly, first[1].financial.cash_flow_monthly)

    def test_custom_scenario_and_resilience_tests(self):
        scenarios = build_standard_scenarios(self.inputs, "Investisseur locatif", {"annual_interest_rate": 6.5, "expense_multiplier": 1.2})
        self.assertEqual(scenarios[-1].name, "Personnalisé")
        resilience, status = build_resilience_tests(self.inputs, "Investisseur locatif")
        self.assertEqual(len(resilience), 5)
        self.assertIn(status, {"résistant", "sensible", "fragile", "données insuffisantes"})
        self.assertEqual(resilience[0].name, "Taux +1 point")


if __name__ == "__main__":
    unittest.main()
