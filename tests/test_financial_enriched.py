"""Tests for enriched deterministic financial calculations."""

import unittest

from calculations.real_estate import PropertyInputs, calculate_analysis


class EnrichedFinancialTests(unittest.TestCase):
    def setUp(self):
        self.inputs = PropertyInputs(
            price=500_000, down_payment=100_000, annual_interest_rate=5.0, amortization_years=25,
            municipal_taxes_annual=3_600, school_taxes_annual=400, insurance_monthly=100,
            condo_fees_monthly=0, rental_income_monthly=3_200, other_expenses_monthly=200,
            household_income_annual=120_000, other_debt_payments_monthly=500, vacancy_rate_pct=10,
            maintenance_monthly=100, management_monthly=100, owner_paid_utilities_monthly=100,
            capital_reserve_monthly=100, initial_repairs=10_000, acquisition_costs=10_000,
            other_income_monthly=200, rent_growth_annual_pct=2, expense_growth_annual_pct=2,
            holding_period_years=5,
        )

    def test_vacancy_and_noi_exclude_debt_service(self):
        result = calculate_analysis(self.inputs)
        self.assertAlmostEqual(result.gross_rental_income_monthly, 3_400)
        self.assertAlmostEqual(result.effective_rental_income_monthly, 3_080)
        self.assertAlmostEqual(result.operating_expenses_monthly, 1_033.33, places=2)
        self.assertAlmostEqual(result.net_operating_income_annual, 24_560, places=2)
        self.assertAlmostEqual(result.actual_capital_invested, 120_000)
        self.assertAlmostEqual(result.cash_on_cash_return, result.cash_flow_monthly * 12 / 120_000 * 100)

    def test_affordability_is_available_only_with_household_income(self):
        result = calculate_analysis(self.inputs)
        self.assertIsNotNone(result.housing_cost_ratio)
        no_income = PropertyInputs(**{**self.inputs.__dict__, "household_income_annual": None})
        self.assertIsNone(calculate_analysis(no_income).housing_cost_ratio)


if __name__ == "__main__":
    unittest.main()
