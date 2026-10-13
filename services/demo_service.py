"""Public sample uses the production calculation engine and no real property."""
import json
from dataclasses import asdict

from calculations.real_estate import PropertyInputs, calculate_analysis
from domain.immoengine import evaluate_immoengine
from domain.scenarios import build_standard_scenarios, build_resilience_tests


def demo_inputs(price=500_000.0, rental_income=4_000.0, interest=5.0):
    return PropertyInputs(price=price, down_payment=100_000, annual_interest_rate=interest,
                          amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400,
                          insurance_monthly=150, condo_fees_monthly=0, rental_income_monthly=rental_income,
                          other_expenses_monthly=100, vacancy_rate_pct=3, maintenance_monthly=150,
                          capital_reserve_monthly=150, acquisition_costs=10_000, initial_repairs=10_000)


def demo_snapshot(inputs=None):
    inputs = inputs or demo_inputs()
    financial = calculate_analysis(inputs)
    engine = evaluate_immoengine(inputs, financial, "Investisseur locatif")
    scenarios = build_standard_scenarios(inputs, "Investisseur locatif")
    tests, status = build_resilience_tests(inputs, "Investisseur locatif")
    result = {"id": 0, "is_demo": True, "property_name": "Duplex fictif — DÉMONSTRATION", "created_at": "Exemple fictif, sans adresse réelle",
              "user_profile": "Investisseur locatif", "price": inputs.price, "down_payment": inputs.down_payment,
              "rental_income": inputs.rental_income_monthly, "monthly_expenses": financial.total_monthly_expenses,
              "cash_flow": financial.cash_flow_monthly, "cash_on_cash_return": financial.cash_on_cash_return,
              "capitalization_rate": financial.capitalization_rate, "debt_service_coverage_ratio": financial.debt_service_coverage_ratio,
              "engine_version": "ImmoEngine — démonstration calculée", "data_provenance": "Hypothèses entièrement fictives. Aucun dossier réel, aucun prix de vente observé.",
              "immo_score": engine.score, "confidence_index": engine.confidence_index, "engine_verdict": engine.verdict,
              "financial_inputs_json": json.dumps({**asdict(inputs), "_property_type": "Duplex"}),
              "scenarios_json": json.dumps([item.to_snapshot() for item in scenarios]),
              "resilience_json": json.dumps({"status": status, "tests": [item.to_snapshot() for item in tests]}),
              "immovalue_json": "{}", "official_role_snapshot_json": "{}", "market_context_json": "[]"}
    for field, value in (("positive_factors", engine.positive_factors), ("negative_factors", engine.negative_factors),
                         ("missing_data", engine.missing_data), ("recommended_checks", engine.recommended_checks),
                         ("immodna", engine.to_snapshot()["dimensions"])):
        result[field + "_json"] = json.dumps(value)
    return result, financial
