"""Deterministic and explainable ImmoEngine v1: no market-value estimation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Optional

from calculations.real_estate import AnalysisResult, PropertyInputs, monthly_mortgage_payment, validate_inputs


PROFILE_WEIGHTS = {
    "Premier acheteur": {"finances": 45, "abordabilite": 30, "rentabilite": 0, "securite": 10, "financement": 15},
    "Investisseur locatif": {"finances": 20, "abordabilite": 0, "rentabilite": 35, "securite": 25, "financement": 20},
    "Propriétaire": {"finances": 40, "abordabilite": 20, "rentabilite": 0, "securite": 20, "financement": 20},
    "Courtier ou analyste": {"finances": 25, "abordabilite": 15, "rentabilite": 20, "securite": 20, "financement": 20},
}

LEGACY_PROFILE_ALIASES = {
    "Investisseur": "Investisseur locatif",
    "Propriétaire occupant": "Propriétaire",
    "Courtier / professionnel": "Courtier ou analyste",
    "Curieux": "Premier acheteur",
}


@dataclass(frozen=True)
class EngineDimension:
    label: str
    score: Optional[float]
    available: bool
    positive_factors: list[str]
    negative_factors: list[str]
    missing_data: list[str]


@dataclass(frozen=True)
class ImmoEngineResult:
    profile: str
    score: Optional[float]
    confidence_index: int
    verdict: str
    dimensions: dict[str, EngineDimension]
    positive_factors: list[str]
    negative_factors: list[str]
    missing_data: list[str]
    recommended_checks: list[str]

    def to_snapshot(self) -> dict:
        """Produce a JSON-safe snapshot to retain with a saved analysis."""
        return asdict(self)


def canonical_profile(profile: str) -> str:
    """Accept legacy MVP profile values without changing historical accounts."""
    profile = LEGACY_PROFILE_ALIASES.get(profile, profile)
    return profile if profile in PROFILE_WEIGHTS else "Investisseur locatif"


def evaluate_immoengine(inputs: PropertyInputs, result: AnalysisResult | None, profile: str) -> ImmoEngineResult:
    """Score only user-entered assumptions and derived financial calculations.

    No market, city, comparable, estimate, AI, or simulated dataset is imported by
    this module. A dimension without sufficient evidence is left unavailable.
    """
    profile = canonical_profile(profile)
    validation_errors = validate_inputs(inputs)
    if validation_errors or result is None:
        missing = ["Hypothèses financières valides et complètes"]
        return ImmoEngineResult(
            profile, None, 0, "données insuffisantes", _unavailable_dimensions(missing), [],
            ["Les hypothèses financières ne permettent pas un calcul fiable."], missing,
            ["Corrigez les champs financiers indiqués avant d'interpréter l'analyse."],
        )

    dimensions = {
        "finances": _financial_structure(inputs),
        "abordabilite": _affordability(),
        "rentabilite": _rental_profitability(inputs, result),
        "securite": _safety_margin(inputs, result),
        "financement": _financing_sensitivity(inputs, result),
    }
    available_weight = sum(PROFILE_WEIGHTS[profile][key] for key, item in dimensions.items() if item.available)
    total_weight = sum(PROFILE_WEIGHTS[profile].values())
    missing_data = _unique(item for dimension in dimensions.values() for item in dimension.missing_data)
    positives = _unique(item for dimension in dimensions.values() for item in dimension.positive_factors)
    negatives = _unique(item for dimension in dimensions.values() for item in dimension.negative_factors)

    if available_weight < total_weight * 0.50:
        score = None
        verdict = "données insuffisantes"
    else:
        weighted_score = sum(
            (dimension.score or 0) * PROFILE_WEIGHTS[profile][key]
            for key, dimension in dimensions.items() if dimension.available
        )
        score = round(_clamp(weighted_score / available_weight, 0, 100), 1)
        verdict = _verdict(score, _confidence(inputs, result, profile))
    confidence = _confidence(inputs, result, profile)
    checks = _recommended_checks(dimensions)
    return ImmoEngineResult(profile, score, confidence, verdict, dimensions, positives[:5], negatives[:5], missing_data, checks)


def _financial_structure(inputs: PropertyInputs) -> EngineDimension:
    ratio = inputs.down_payment / inputs.price
    # 5 % gives 0; 35 % or more gives 100. This evaluates financing structure,
    # not household affordability (which requires income and debt information).
    score = _clamp((ratio - 0.05) / 0.30 * 100, 0, 100)
    positives = [f"Mise de fonds de {ratio * 100:.1f} % du prix."] if ratio >= 0.20 else []
    negatives = [f"Mise de fonds de {ratio * 100:.1f} % : la structure de financement est plus serrée."] if ratio < 0.20 else []
    return EngineDimension("Finances", round(score, 1), True, positives, negatives, [])


def _affordability() -> EngineDimension:
    missing = ["Revenu brut du ménage", "Autres dettes et obligations mensuelles"]
    return EngineDimension("Abordabilité", None, False, [], [], missing)


def _rental_profitability(inputs: PropertyInputs, result: AnalysisResult) -> EngineDimension:
    if inputs.rental_income_monthly <= 0:
        return EngineDimension("Rentabilité locative", None, False, [], [], ["Revenus locatifs attendus"])
    cap_score = _clamp(result.capitalization_rate / 7 * 100, 0, 100)
    coc_score = _clamp((result.cash_on_cash_return + 5) / 17 * 100, 0, 100)
    cash_score = _clamp((result.cash_flow_monthly + 500) / 1500 * 100, 0, 100)
    score = 0.45 * cap_score + 0.30 * coc_score + 0.25 * cash_score
    positives = []
    negatives = []
    if result.cash_flow_monthly >= 0:
        positives.append(f"Flux de trésorerie mensuel positif : {result.cash_flow_monthly:,.0f} $.".replace(",", " "))
    else:
        negatives.append(f"Flux de trésorerie mensuel négatif : {result.cash_flow_monthly:,.0f} $.".replace(",", " "))
    if result.capitalization_rate >= 5:
        positives.append(f"Taux de capitalisation de {result.capitalization_rate:.2f} %.")
    else:
        negatives.append(f"Taux de capitalisation de {result.capitalization_rate:.2f} % : à contextualiser.")
    return EngineDimension("Rentabilité locative", round(_clamp(score, 0, 100), 1), True, positives, negatives, [])


def _safety_margin(inputs: PropertyInputs, result: AnalysisResult) -> EngineDimension:
    if inputs.rental_income_monthly <= 0:
        return EngineDimension("Résistance aux imprévus", None, False, [], [], ["Revenus locatifs attendus pour calculer une marge de sécurité"])
    dscr_score = _clamp((result.debt_service_coverage_ratio - 0.80) / 0.50 * 100, 0, 100)
    cash_ratio = result.cash_flow_monthly / inputs.rental_income_monthly
    cash_score = _clamp((cash_ratio + 0.10) / 0.30 * 100, 0, 100)
    score = 0.65 * dscr_score + 0.35 * cash_score
    positives = [f"DSCR de {result.debt_service_coverage_ratio:.2f}x couvre le service de la dette."] if result.debt_service_coverage_ratio >= 1.20 else []
    negatives = [f"DSCR de {result.debt_service_coverage_ratio:.2f}x : marge de dette limitée."] if result.debt_service_coverage_ratio < 1.20 else []
    return EngineDimension("Résistance aux imprévus", round(_clamp(score, 0, 100), 1), True, positives, negatives, [])


def _financing_sensitivity(inputs: PropertyInputs, result: AnalysisResult) -> EngineDimension:
    stressed_payment = monthly_mortgage_payment(result.loan_amount, inputs.annual_interest_rate + 1, inputs.amortization_years)
    increase = (stressed_payment - result.monthly_payment) / result.monthly_payment if result.monthly_payment else 0
    score = _clamp((0.20 - increase) / 0.15 * 100, 0, 100)
    positives = [f"Une hausse de 1 point du taux augmente le paiement d'environ {increase * 100:.1f} %."] if increase <= 0.10 else []
    negatives = [f"Une hausse de 1 point du taux augmente le paiement d'environ {increase * 100:.1f} %."] if increase > 0.10 else []
    return EngineDimension("Sensibilité au financement", round(score, 1), True, positives, negatives, [])


def _confidence(inputs: PropertyInputs, result: AnalysisResult, profile: str) -> int:
    """Measure completeness of stated assumptions, never purchase likelihood."""
    core = all(isfinite(value) for value in (inputs.price, inputs.down_payment, inputs.annual_interest_rate, result.monthly_payment))
    operating = all(isfinite(value) and value >= 0 for value in (inputs.municipal_taxes_annual, inputs.school_taxes_annual, inputs.insurance_monthly, inputs.condo_fees_monthly, inputs.other_expenses_monthly))
    rental_ready = inputs.rental_income_monthly > 0 or profile != "Investisseur locatif"
    score = (35 if core else 0) + (25 if operating else 0) + (20 if rental_ready else 0) + 20
    # All inputs are user-declared and no property/market verification is present;
    # confidence is therefore capped at 80 and is not a recommendation probability.
    return min(score, 80)


def _verdict(score: float, confidence: int) -> str:
    if confidence < 50:
        return "à approfondir"
    if score >= 70:
        return "favorable selon vos hypothèses"
    if score >= 45:
        return "à approfondir"
    return "prudence"


def _recommended_checks(dimensions: dict[str, EngineDimension]) -> list[str]:
    checks = ["Vérifiez les taxes, assurances, frais et revenus avec des documents à jour."]
    if not dimensions["abordabilite"].available:
        checks.append("Ajoutez le revenu brut du ménage et les autres dettes pour évaluer l'abordabilité.")
    if not dimensions["rentabilite"].available:
        checks.append("Ajoutez des revenus locatifs réalistes avant d'interpréter la rentabilité.")
    checks.append("Testez un scénario de taux plus élevé et prévoyez les dépenses non incluses (vacance, CAPEX, frais d'acquisition).")
    return checks


def _unavailable_dimensions(missing: list[str]) -> dict[str, EngineDimension]:
    return {key: EngineDimension(label, None, False, [], [], missing) for key, label in (
        ("finances", "Finances"), ("abordabilite", "Abordabilité"), ("rentabilite", "Rentabilité locative"),
        ("securite", "Résistance aux imprévus"), ("financement", "Sensibilité au financement"),
    )}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _unique(items):
    return list(dict.fromkeys(items))
