"""Deterministic scenario and resilience calculations for ImmoRadar."""

from dataclasses import asdict, dataclass, replace

from calculations.real_estate import AnalysisResult, PropertyInputs, calculate_analysis
from domain.immoengine import ImmoEngineResult, evaluate_immoengine


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    inputs: PropertyInputs
    financial: AnalysisResult
    engine: ImmoEngineResult
    description: str

    def to_snapshot(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": asdict(self.inputs),
            "financial": asdict(self.financial),
            "engine": self.engine.to_snapshot(),
        }


def build_standard_scenarios(inputs: PropertyInputs, profile: str, custom: dict | None = None) -> list[ScenarioResult]:
    """Build prudent, base, favourable and optional custom scenarios.

    Favourable is an illustrative sensitivity case only, never a forecast.
    """
    scenarios = [
        _evaluate("Prudent", _prudent(inputs), profile, "Taux plus élevé, revenus réduits, vacance et dépenses accrues."),
        _evaluate("Scénario de base", inputs, profile, "Vos hypothèses actuelles."),
        _evaluate("Favorable", _favourable(inputs), profile, "Illustration favorable, non présentée comme une prévision."),
    ]
    if custom:
        scenarios.append(_evaluate("Personnalisé", apply_custom_scenario(inputs, custom), profile, "Modifications choisies par l'utilisateur."))
    return scenarios


def apply_custom_scenario(inputs: PropertyInputs, custom: dict) -> PropertyInputs:
    """Apply only explicit user overrides to a base scenario."""
    expense_multiplier = custom.get("expense_multiplier", 1.0)
    expenses = {
        "other_expenses_monthly": inputs.other_expenses_monthly * expense_multiplier,
        "maintenance_monthly": inputs.maintenance_monthly * expense_multiplier,
        "management_monthly": inputs.management_monthly * expense_multiplier,
        "owner_paid_utilities_monthly": inputs.owner_paid_utilities_monthly * expense_multiplier,
        "capital_reserve_monthly": inputs.capital_reserve_monthly * expense_multiplier,
    }
    return replace(inputs, **expenses, **{key: value for key, value in custom.items() if key != "expense_multiplier"})


def build_resilience_tests(inputs: PropertyInputs, profile: str) -> tuple[list[ScenarioResult], str]:
    """Run documented downside sensitivities and classify financial resilience."""
    tests = [
        _evaluate("Taux +1 point", replace(inputs, annual_interest_rate=inputs.annual_interest_rate + 1), profile, "Hausse de taux de 1 point."),
        _evaluate("Revenus -10 %", replace(inputs, rental_income_monthly=inputs.rental_income_monthly * 0.90, other_income_monthly=inputs.other_income_monthly * 0.90), profile, "Réduction de 10 % des revenus."),
        _evaluate("Dépenses +10 %", apply_custom_scenario(inputs, {"expense_multiplier": 1.10}), profile, "Hausse de 10 % des dépenses d'exploitation variables."),
        _evaluate("Vacance accrue", replace(inputs, vacancy_rate_pct=min(100, inputs.vacancy_rate_pct + 5)), profile, "Hausse de 5 points du taux de vacance."),
        _evaluate("Combinaison défavorable", apply_custom_scenario(replace(
            inputs, annual_interest_rate=inputs.annual_interest_rate + 1,
            rental_income_monthly=inputs.rental_income_monthly * 0.90,
            other_income_monthly=inputs.other_income_monthly * 0.90,
            vacancy_rate_pct=min(100, inputs.vacancy_rate_pct + 5),
            initial_repairs=inputs.initial_repairs * 1.10,
        ), {"expense_multiplier": 1.10}), profile, "Taux +1 point, revenus -10 %, vacance +5 points et dépenses +10 %."),
    ]
    if any(test.engine.score is None for test in tests):
        return tests, "données insuffisantes"
    if all(test.financial.cash_flow_monthly >= 0 and test.financial.debt_service_coverage_ratio >= 1.10 for test in tests):
        return tests, "résistant"
    combination = tests[-1].financial
    if combination.cash_flow_monthly >= 0 and combination.debt_service_coverage_ratio >= 1.00:
        return tests, "sensible"
    return tests, "fragile"


def _prudent(inputs: PropertyInputs) -> PropertyInputs:
    return apply_custom_scenario(replace(
        inputs,
        annual_interest_rate=inputs.annual_interest_rate + 1,
        rental_income_monthly=inputs.rental_income_monthly * 0.95,
        other_income_monthly=inputs.other_income_monthly * 0.95,
        vacancy_rate_pct=min(100, inputs.vacancy_rate_pct + 3),
    ), {"expense_multiplier": 1.10})


def _favourable(inputs: PropertyInputs) -> PropertyInputs:
    return apply_custom_scenario(replace(
        inputs,
        annual_interest_rate=max(0, inputs.annual_interest_rate - 0.50),
        rental_income_monthly=inputs.rental_income_monthly * 1.05,
        other_income_monthly=inputs.other_income_monthly * 1.05,
        vacancy_rate_pct=max(0, inputs.vacancy_rate_pct - 1),
    ), {"expense_multiplier": 0.95})


def _evaluate(name: str, scenario_inputs: PropertyInputs, profile: str, description: str) -> ScenarioResult:
    financial = calculate_analysis(scenario_inputs)
    return ScenarioResult(name, scenario_inputs, financial, evaluate_immoengine(scenario_inputs, financial, profile), description)
