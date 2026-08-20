"""Deterministic comparison of two immutable, user-owned analysis snapshots."""

from __future__ import annotations

import json
from typing import Any

from services.analysis_service import get_user_analyses_for_comparison


class ComparisonAccessError(PermissionError):
    """Raised without disclosing whether an unavailable dossier belongs to someone else."""


def _json_object(raw: str | None, fallback: Any) -> Any:
    try:
        value = json.loads(raw or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
    return value if isinstance(value, type(fallback)) else fallback


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _scenario_financial(analysis: dict[str, Any], name: str) -> dict[str, Any]:
    for scenario in _json_object(analysis.get("scenarios_json"), []):
        if isinstance(scenario, dict) and scenario.get("name") == name:
            return scenario.get("financial") if isinstance(scenario.get("financial"), dict) else {}
    return {}


def _resilience_financial(analysis: dict[str, Any]) -> dict[str, Any]:
    resilience = _json_object(analysis.get("resilience_json"), {})
    for item in resilience.get("tests", []) if isinstance(resilience, dict) else []:
        if isinstance(item, dict) and item.get("name") == "Taux +1 point":
            return item.get("financial") if isinstance(item.get("financial"), dict) else {}
    return {}


def _immovalue_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    """Read the immutable ImmoValue payload, including an unavailable draft."""

    return _json_object(analysis.get("immovalue_json"), {})


def _immovalue(analysis: dict[str, Any]) -> dict[str, Any]:
    value = _immovalue_payload(analysis)
    return value if value.get("available") else {}


def _snapshot(analysis: dict[str, Any]) -> dict[str, Any]:
    """Extract displayable stored fields only; this function never recalculates values."""
    immovalue_payload = _immovalue_payload(analysis)
    immovalue = immovalue_payload if immovalue_payload.get("available") else {}
    official_role = _json_object(analysis.get("official_role_snapshot_json"), {})
    financial_inputs = _json_object(analysis.get("financial_inputs_json"), {})
    base = _scenario_financial(analysis, "Scénario de base")
    stressed = _resilience_financial(analysis)
    return {
        "id": int(analysis["id"]),
        "name": analysis.get("property_name") or "Dossier sans nom",
        "date": analysis.get("created_at"),
        "profile": analysis.get("user_profile") or "Investisseur locatif",
        "property_type": financial_inputs.get("property_type") or financial_inputs.get("property_type_label"),
        "price": _number(analysis.get("price")),
        "municipal_value": _number(official_role.get("total_value")),
        "municipal_role_year": official_role.get("role_year"),
        "municipal_reference_date": official_role.get("reference_date"),
        "municipal_source": official_role.get("source"),
        "immovalue": _number(immovalue.get("estimated_value")),
        "immovalue_low": _number(immovalue.get("low")),
        "immovalue_high": _number(immovalue.get("high")),
        "immovalue_confidence": _number(immovalue.get("confidence")),
        # The asking price belongs to the declared subject, not to an
        # ImmoValue result. It therefore remains available when the estimate
        # is still waiting for three comparable sales.
        "asking_price": _number(immovalue_payload.get("subject", {}).get("asking_price")) if isinstance(immovalue_payload.get("subject"), dict) else None,
        "monthly_payment": _number(base.get("monthly_payment")) or _number(financial_inputs.get("monthly_payment")),
        "monthly_expenses": _number(analysis.get("monthly_expenses")),
        "rental_income": _number(analysis.get("rental_income")),
        "cash_flow": _number(analysis.get("cash_flow")),
        "cash_on_cash_return": _number(analysis.get("cash_on_cash_return")),
        "capitalization_rate": _number(analysis.get("capitalization_rate")),
        "dscr": _number(analysis.get("debt_service_coverage_ratio")),
        "score": _number(analysis.get("immo_score")),
        "confidence": _number(analysis.get("confidence_index")),
        "engine_version": analysis.get("engine_version"),
        "base_cash_flow": _number(base.get("cash_flow_monthly")) or _number(analysis.get("cash_flow")),
        "rate_up_cash_flow": _number(stressed.get("cash_flow_monthly")),
    }


def _relation(a: float | None, b: float | None, higher_is_better: bool) -> str:
    if a is None or b is None:
        return "non_comparable"
    if abs(a - b) < 0.005:
        return "égalité"
    if (a > b) == higher_is_better:
        return "avantage_a"
    return "avantage_b"


_INDICATORS = (
    ("municipal_value", "Valeur municipale officielle (repère fiscal)", True, False),
    ("immovalue", "Estimation ImmoValue", True, False),
    ("asking_price", "Prix demandé", False, False),
    ("monthly_payment", "Paiement hypothécaire mensuel", False, True),
    ("monthly_expenses", "Dépenses mensuelles", False, True),
    ("rental_income", "Revenus locatifs mensuels", True, True),
    ("cash_flow", "Flux de trésorerie mensuel", True, True),
    ("cash_on_cash_return", "Rendement sur la mise", True, True),
    ("capitalization_rate", "Taux de capitalisation", True, True),
    ("dscr", "Capacité à couvrir la dette (DSCR)", True, True),
    ("score", "Score ImmoRadar", True, True),
    ("confidence", "Confiance des données", True, True),
)


def _insight(label: str, relation: str) -> str:
    if relation == "avantage_a":
        return f"{label} est plus favorable pour la propriété A selon les instantanés."
    return f"{label} est plus favorable pour la propriété B selon les instantanés."


def compare_saved_analyses(
    user_id: int, analysis_a_id: int, analysis_b_id: int, database_path: str,
) -> dict[str, Any]:
    """Compare two saved snapshots after enforcing their common owner in SQLite."""
    if analysis_a_id == analysis_b_id:
        raise ValueError("Choisissez deux dossiers différents.")
    analyses = get_user_analyses_for_comparison(user_id, analysis_a_id, analysis_b_id, database_path)
    if len(analyses) != 2:
        raise ComparisonAccessError("Les dossiers demandés ne sont pas disponibles dans votre espace.")

    a, b = (_snapshot(analysis) for analysis in analyses)
    indicators = []
    strengths = {"a": [], "b": []}
    checks = {"a": [], "b": []}
    for key, label, higher_is_better, comparable in _INDICATORS:
        relation = _relation(a[key], b[key], higher_is_better) if comparable else "non_comparable"
        indicators.append({"key": key, "label": label, "a": a[key], "b": b[key], "relation": relation})
        if relation == "avantage_a" and len(strengths["a"]) < 3:
            strengths["a"].append(_insight(label, relation))
        elif relation == "avantage_b" and len(strengths["b"]) < 3:
            strengths["b"].append(_insight(label, relation))
        if comparable and a[key] is None and len(checks["a"]) < 3:
            checks["a"].append(f"{label} n’est pas disponible dans cet instantané.")
        if comparable and b[key] is None and len(checks["b"]) < 3:
            checks["b"].append(f"{label} n’est pas disponible dans cet instantané.")

    if a["profile"] != b["profile"]:
        conclusion = "Les profils sauvegardés diffèrent : la comparaison reste descriptive et ne tranche pas entre les dossiers."
    elif not strengths["a"] and not strengths["b"]:
        conclusion = "Les instantanés disponibles ne distinguent pas clairement les deux propriétés selon vos hypothèses sauvegardées."
    elif len(strengths["a"]) > len(strengths["b"]):
        conclusion = f"Pour le profil « {a['profile']} », la propriété A semble mieux alignée avec vos hypothèses sauvegardées sur les indicateurs disponibles."
    elif len(strengths["b"]) > len(strengths["a"]):
        conclusion = f"Pour le profil « {a['profile']} », la propriété B semble mieux alignée avec vos hypothèses sauvegardées sur les indicateurs disponibles."
    else:
        conclusion = f"Pour le profil « {a['profile']} », les deux propriétés présentent des points d’alignement différents selon vos hypothèses sauvegardées."

    return {
        "a": a,
        "b": b,
        "indicators": indicators,
        "strengths": strengths,
        "checks": checks,
        "conclusion": conclusion,
        "engine_versions_differ": a["engine_version"] != b["engine_version"],
        "scenarios": {
            "current": {"label": "Situation actuelle", "a": a["base_cash_flow"], "b": b["base_cash_flow"]},
            "rate_up": {"label": "Hausse de taux de +1 point", "a": a["rate_up_cash_flow"], "b": b["rate_up_cash_flow"]},
        },
    }
