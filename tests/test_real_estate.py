import unittest

from calculations.real_estate import PropertyInputs, calculate_analysis, monthly_mortgage_payment, validate_inputs


class RealEstateCalculationsTests(unittest.TestCase):
    def setUp(self):
        self.inputs = PropertyInputs(
            price=500_000,
            down_payment=100_000,
            annual_interest_rate=5.0,
            amortization_years=25,
            municipal_taxes_annual=3_600,
            school_taxes_annual=400,
            insurance_monthly=100,
            condo_fees_monthly=0,
            rental_income_monthly=3_200,
            other_expenses_monthly=200,
        )

    def test_standard_mortgage_payment(self):
        payment = monthly_mortgage_payment(400_000, 5.0, 25)
        self.assertAlmostEqual(payment, 2_326.42, places=2)

    def test_analysis_ratios_are_calculated_from_inputs(self):
        result = calculate_analysis(self.inputs)
        self.assertAlmostEqual(result.operating_expenses_monthly, 633.33, places=2)
        self.assertAlmostEqual(result.total_monthly_expenses, 2_959.75, places=2)
        self.assertAlmostEqual(result.net_operating_income_annual, 30_800.00, places=2)
        self.assertAlmostEqual(result.cash_flow_monthly, 240.25, places=2)
        self.assertGreater(result.debt_service_coverage_ratio, 1)

    def test_invalid_down_payment_is_rejected(self):
        invalid = PropertyInputs(**{**self.inputs.__dict__, "down_payment": 500_000})
        self.assertTrue(validate_inputs(invalid))

    def test_zero_interest_payment_is_supported(self):
        self.assertAlmostEqual(monthly_mortgage_payment(120_000, 0, 10), 1_000)


if __name__ == "__main__":
    unittest.main()
