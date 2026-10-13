"""Prepare a new editable draft from one user-owned saved analysis.

The service restores only user-entered financial assumptions and declared
subject fields.  It deliberately excludes addresses, public-role matches and
any external lookup state: reopening a dossier never starts a public search.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from repositories.sqlite_repository import SQLiteRepository


class AnalysisReopenAccessError(PermissionError):
    """Raised without disclosing whether a dossier belongs to someone else."""


INPUT_KEY_MAP = {
    "price": "property_price",
    "down_payment": "down_payment",
    "annual_interest_rate": "mortgage_rate",
    "amortization_years": "amortization_years",
    "municipal_taxes_annual": "municipal_taxes",
    "school_taxes_annual": "school_taxes",
    "insurance_monthly": "insurance",
    "condo_fees_monthly": "condo_fees",
    "rental_income_monthly": "rental_income",
    "other_expenses_monthly": "other_expenses",
    "household_income_annual": "household_income",
    "other_debt_payments_monthly": "other_debts",
    "vacancy_rate_pct": "vacancy_rate",
    "maintenance_monthly": "maintenance",
    "management_monthly": "management",
    "owner_paid_utilities_monthly": "utilities",
    "capital_reserve_monthly": "capital_reserve",
    "initial_repairs": "initial_repairs",
    "acquisition_costs": "acquisition_costs",
    "other_income_monthly": "other_income",
    "rent_growth_annual_pct": "rent_growth",
    "expense_growth_annual_pct": "expense_growth",
    "holding_period_years": "holding_period",
}


def _object(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _numeric_inputs(values: dict[str, Any]) -> dict[str, float | int]:
    restored: dict[str, float | int] = {}
    for stored_key, session_key in INPUT_KEY_MAP.items():
        value = values.get(stored_key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            restored[session_key] = value
    return restored


def _custom_scenario(analysis, financial):
    try:
        scenarios = json.loads(analysis.get("scenarios_json") or "[]")
    except (TypeError, ValueError):
        return None
    if not isinstance(scenarios, list):
        return None
    for scenario in scenarios:
        if not isinstance(scenario, dict) or scenario.get("name") != "Personnalisé" or not isinstance(scenario.get("inputs"), dict):
            continue
        inputs = scenario["inputs"]
        keys = ("price", "down_payment", "annual_interest_rate", "rental_income_monthly", "vacancy_rate_pct", "initial_repairs", "holding_period_years")
        result = {key: inputs[key] for key in keys if isinstance(inputs.get(key), (int, float)) and not isinstance(inputs[key], bool) and math.isfinite(inputs[key])}
        if len(result) != len(keys):
            return None
        for key in ("other_expenses_monthly", "maintenance_monthly", "management_monthly", "owner_paid_utilities_monthly", "capital_reserve_monthly"):
            base, altered = financial.get(key), inputs.get(key)
            if isinstance(base, (int, float)) and base > 0 and isinstance(altered, (int, float)):
                result["expense_multiplier"] = altered / base
                break
        result.setdefault("expense_multiplier", 1.0)
        if not (0.5 <= result["expense_multiplier"] <= 2 and 0 <= result["annual_interest_rate"] <= 25
                and 0 < result["down_payment"] < result["price"] and 0 <= result["vacancy_rate_pct"] <= 100
                and result["rental_income_monthly"] >= 0 and result["initial_repairs"] >= 0
                and 1 <= result["holding_period_years"] <= 40):
            return None
        return result
    return None


def prepare_reopen_draft(user_id: int, analysis_id: int, database_path: Path | str) -> dict[str, Any]:
    """Return a safe, ownership-scoped payload for a new editable draft."""

    analysis = SQLiteRepository(database_path).get_owned_analysis(user_id, analysis_id)
    if analysis is None:
        raise AnalysisReopenAccessError("Le dossier demandé n’est pas disponible dans votre espace.")
    financial = _object(analysis.get("financial_inputs_json"))
    immovalue = _object(analysis.get("immovalue_json"))
    subject = immovalue.get("subject") if isinstance(immovalue.get("subject"), dict) else {}
    asking_price = subject.get("asking_price")
    if not isinstance(asking_price, (int, float)) or isinstance(asking_price, bool):
        asking_price = None
    objective = financial.get("_analysis_objective")
    property_type = financial.get("_property_type") or subject.get("property_type")
    return {
        "owner_id": int(user_id),
        "custom_scenario": _custom_scenario(analysis, financial),
        "source_analysis_id": int(analysis_id),
        "property_name": str(analysis.get("property_name") or ""),
        "profile": str(analysis.get("user_profile") or ""),
        "objective": str(objective) if isinstance(objective, str) else "",
        "property_type": str(property_type) if isinstance(property_type, str) else "",
        "financial_values": _numeric_inputs(financial),
        "mortgage_renewal_date": financial.get("mortgage_renewal_date") if isinstance(financial.get("mortgage_renewal_date"), str) else None,
        "asking_price": asking_price,
    }
