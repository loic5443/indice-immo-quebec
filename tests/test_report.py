"""PDF report integrity tests using a saved-analysis-shaped snapshot."""

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from calculations.real_estate import PropertyInputs, calculate_analysis
from domain.immoengine import evaluate_immoengine
from domain.scenarios import build_resilience_tests, build_standard_scenarios
from pypdf import PdfReader
from services.report_service import generate_report_pdf


class ReportTests(unittest.TestCase):
    def setUp(self):
        inputs = PropertyInputs(
            price=500_000, down_payment=125_000, annual_interest_rate=5.0, amortization_years=25,
            municipal_taxes_annual=3_600, school_taxes_annual=400, insurance_monthly=100,
            condo_fees_monthly=0, rental_income_monthly=3_600, other_expenses_monthly=200,
            household_income_annual=120_000, vacancy_rate_pct=3, maintenance_monthly=100,
            capital_reserve_monthly=100, holding_period_years=5,
        )
        result = calculate_analysis(inputs)
        engine = evaluate_immoengine(inputs, result, "Investisseur locatif")
        scenarios = [item.to_snapshot() for item in build_standard_scenarios(inputs, engine.profile)]
        resilience, status = build_resilience_tests(inputs, engine.profile)
        self.analysis = {
            "id": 99, "property_name": "Exemple fictif - Montréal", "created_at": "2026-07-28 12:00 UTC",
            "user_profile": engine.profile, "immo_score": engine.score, "confidence_index": engine.confidence_index,
            "engine_verdict": engine.verdict, "engine_version": "ImmoEngine 1.1.0-financial-scenarios",
            "data_provenance": "Hypothèses saisies par l'utilisateur; calculs déterministes; aucune estimation de valeur.",
            "price": inputs.price, "down_payment": inputs.down_payment, "rental_income": inputs.rental_income_monthly,
            "monthly_expenses": result.total_monthly_expenses, "cash_flow": result.cash_flow_monthly,
            "cash_on_cash_return": result.cash_on_cash_return, "capitalization_rate": result.capitalization_rate,
            "debt_service_coverage_ratio": result.debt_service_coverage_ratio,
            "financial_inputs_json": __import__("json").dumps(asdict(inputs), ensure_ascii=False),
            "scenarios_json": __import__("json").dumps(scenarios, ensure_ascii=False),
            "resilience_json": __import__("json").dumps({"status": status, "tests": [item.to_snapshot() for item in resilience]}, ensure_ascii=False),
            "immodna_json": __import__("json").dumps(engine.to_snapshot()["dimensions"], ensure_ascii=False),
            "positive_factors_json": __import__("json").dumps(engine.positive_factors, ensure_ascii=False),
            "negative_factors_json": __import__("json").dumps(engine.negative_factors, ensure_ascii=False),
            "missing_data_json": __import__("json").dumps(engine.missing_data, ensure_ascii=False),
            "recommended_checks_json": __import__("json").dumps(engine.recommended_checks, ensure_ascii=False),
        }

    def test_report_is_valid_french_pdf_with_required_sections(self):
        content = generate_report_pdf(self.analysis)
        self.assertTrue(content.startswith(b"%PDF"))
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "rapport.pdf"
            path.write_bytes(content)
            reader = PdfReader(path)
            self.assertGreaterEqual(len(reader.pages), 4)
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
        for section in ("ImmoRadar", "Résumé exécutif", "Résultats financiers", "Scénarios", "Tests de résistance", "Avertissement"):
            self.assertIn(section, extracted)
        self.assertIn("Exemple fictif", extracted)
        self.assertIn("Montréal", extracted)
        self.assertIn(str(round(self.analysis["immo_score"])), extracted)


if __name__ == "__main__":
    unittest.main()
