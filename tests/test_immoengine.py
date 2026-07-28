"""Acceptance tests for the deterministic ImmoEngine v1."""

import inspect
import unittest

from calculations.real_estate import PropertyInputs, calculate_analysis
from domain import immoengine
from domain.immoengine import PROFILE_WEIGHTS, evaluate_immoengine


class ImmoEngineTests(unittest.TestCase):
    def setUp(self):
        self.inputs = PropertyInputs(
            price=500_000,
            down_payment=125_000,
            annual_interest_rate=5.0,
            amortization_years=25,
            municipal_taxes_annual=3_600,
            school_taxes_annual=400,
            insurance_monthly=100,
            condo_fees_monthly=0,
            rental_income_monthly=3_600,
            other_expenses_monthly=200,
        )
        self.result = calculate_analysis(self.inputs)

    def test_each_supported_profile_returns_a_bounded_deterministic_result(self):
        for profile in PROFILE_WEIGHTS:
            first = evaluate_immoengine(self.inputs, self.result, profile)
            second = evaluate_immoengine(self.inputs, self.result, profile)
            self.assertEqual(first, second)
            self.assertIsNotNone(first.score)
            self.assertGreaterEqual(first.score, 0)
            self.assertLessEqual(first.score, 100)
            self.assertGreaterEqual(first.confidence_index, 0)
            self.assertLessEqual(first.confidence_index, 100)

    def test_insufficient_inputs_do_not_receive_a_score(self):
        invalid = PropertyInputs(**{**self.inputs.__dict__, "down_payment": self.inputs.price})
        result = evaluate_immoengine(invalid, None, "Investisseur locatif")
        self.assertIsNone(result.score)
        self.assertEqual(result.verdict, "données insuffisantes")

    def test_confidence_is_distinct_from_score(self):
        engine_result = evaluate_immoengine(self.inputs, self.result, "Investisseur locatif")
        self.assertNotEqual(engine_result.confidence_index, engine_result.score)
        self.assertLessEqual(engine_result.confidence_index, 85)
        self.assertIn("Revenu brut du ménage", engine_result.missing_data)

        incomplete_inputs = PropertyInputs(**{**self.inputs.__dict__, "rental_income_monthly": 0})
        incomplete_result = calculate_analysis(incomplete_inputs)
        incomplete_engine = evaluate_immoengine(incomplete_inputs, incomplete_result, "Investisseur locatif")
        self.assertLess(incomplete_engine.confidence_index, engine_result.confidence_index)

    def test_engine_does_not_import_or_use_simulated_market_data(self):
        source = inspect.getsource(immoengine)
        self.assertNotIn("simulated_data", source)
        self.assertNotIn("market_stats", source)

    def test_rental_dimension_is_unavailable_without_rental_income(self):
        owner_inputs = PropertyInputs(**{**self.inputs.__dict__, "rental_income_monthly": 0})
        owner_result = calculate_analysis(owner_inputs)
        engine_result = evaluate_immoengine(owner_inputs, owner_result, "Propriétaire")
        self.assertFalse(engine_result.dimensions["rentabilite"].available)
        self.assertIsNone(engine_result.dimensions["rentabilite"].score)


if __name__ == "__main__":
    unittest.main()
