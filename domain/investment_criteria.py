"""Investor-defined screening of immutable saved values, never an appraisal."""
import json
import math


CRITERIA = {
    "max_price": ("Prix retenu maximal", "price", "max", "$", 0, 100_000_000),
    "min_cash_flow": ("Flux mensuel minimal", "cash_flow", "min", "$/mois", -100_000, 100_000),
    "min_cash_on_cash": ("Rendement sur capital minimal", "cash_on_cash_return", "min", "%", -1000, 1000),
    "min_dscr": ("Couverture de dette minimale", "debt_service_coverage_ratio", "min", "x", 0, 100),
    "min_prudent_cash_flow": ("Flux prudent minimal", "prudent_cash_flow", "min", "$/mois", -100_000, 100_000),
}
RENTAL_KEYS = {"min_cash_flow", "min_cash_on_cash", "min_dscr", "min_prudent_cash_flow"}


def validate_criteria(criteria):
    if not isinstance(criteria, dict) or any(key not in CRITERIA for key in criteria):
        raise ValueError("Les critères sont invalides.")
    for key, value in criteria.items():
        *_, lower, upper = CRITERIA[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError("Les seuils doivent être des nombres finis dans les limites affichées.")
    return {key: float(value) for key, value in criteria.items()}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def screen_snapshot(analysis, criteria):
    criteria = validate_criteria(criteria)
    income = _number(analysis.get("rental_income"))
    try:
        inputs = json.loads(analysis.get("financial_inputs_json") or "{}")
    except (TypeError, ValueError):
        inputs = {}
    if isinstance(inputs, dict):
        rent = _number(inputs.get("rental_income_monthly"))
        other = _number(inputs.get("other_income_monthly"))
        if rent is not None:
            income = rent + (other or 0)
    metrics = {key: _number(analysis.get(key)) for key in ("price", "cash_flow", "cash_on_cash_return", "debt_service_coverage_ratio")}
    metrics["prudent_cash_flow"] = None
    try:
        scenarios = json.loads(analysis.get("scenarios_json") or "[]")
    except (TypeError, ValueError):
        scenarios = []
    if isinstance(scenarios, list):
        for scenario in scenarios:
            if isinstance(scenario, dict) and scenario.get("name") == "Prudent" and isinstance(scenario.get("financial"), dict):
                metrics["prudent_cash_flow"] = _number(scenario["financial"].get("cash_flow_monthly"))
                break
    rows = []
    for key, threshold in criteria.items():
        label, metric, operator, unit, *_ = CRITERIA[key]
        value = metrics[metric]
        if key in RENTAL_KEYS and (income is None or income <= 0):
            value = None
            reason = "Revenus locatifs non renseignés ou non applicables."
        else:
            reason = "Valeur absente de l’instantané." if value is None else "Valeur sauvegardée comparée à votre seuil."
        meets = None if value is None else value <= threshold if operator == "max" else value >= threshold
        rows.append({"key": key, "label": label, "value": value, "threshold": threshold,
                     "operator": operator, "unit": unit, "meets": meets, "reason": reason})
    matched = sum(row["meets"] is True for row in rows)
    failed = sum(row["meets"] is False for row in rows)
    missing = sum(row["meets"] is None for row in rows)
    status = "not_configured" if not rows else "outside" if failed else "incomplete" if missing else "matches"
    return {"status": status, "matched": matched, "failed": failed, "missing": missing, "rows": rows,
            "note": "Vos critères comparent les chiffres sauvegardés. Ils ne constituent ni une évaluation, ni une recommandation d’achat."}


def financing_price_ceiling(inputs, criteria):
    """Solve a purchase-price bound for fixed assumptions, not market value.

    Down payment, taxes, reserves, acquisition costs and rents stay fixed.
    Mortgage insurance, lender qualification and price-dependent taxes are not
    modeled. A result is a mathematical sensitivity, never an offer advice.
    """
    from calculations.real_estate import calculate_analysis, monthly_mortgage_payment
    from domain.scenarios import build_standard_scenarios

    criteria = validate_criteria(criteria)
    if not criteria:
        return {"status": "not_configured", "price": None}
    base = calculate_analysis(inputs)
    if any(key in RENTAL_KEYS for key in criteria) and base.gross_rental_income_monthly <= 0:
        return {"status": "unavailable", "price": None, "reason": "Des revenus locatifs sont nécessaires pour ces critères."}
    coefficient = monthly_mortgage_payment(1, inputs.annual_interest_rate, inputs.amortization_years)
    cash_before_debt = base.net_operating_income_annual / 12
    bounds = []
    for key, threshold in criteria.items():
        if key == "max_price":
            bounds.append((threshold, CRITERIA[key][0]))
        elif key == "min_cash_flow":
            bounds.append((inputs.down_payment + (cash_before_debt - threshold) / coefficient, CRITERIA[key][0]))
        elif key == "min_cash_on_cash":
            required_cash = base.actual_capital_invested * threshold / 1200
            bounds.append((inputs.down_payment + (cash_before_debt - required_cash) / coefficient, CRITERIA[key][0]))
        elif key == "min_dscr":
            if threshold == 0 and cash_before_debt >= 0:
                continue
            allowed_payment = cash_before_debt / threshold if threshold else -1
            bounds.append((inputs.down_payment + allowed_payment / coefficient, CRITERIA[key][0]))
        elif key == "min_prudent_cash_flow":
            try:
                prudent = build_standard_scenarios(inputs, "Investisseur locatif")[0]
            except ValueError:
                return {"status": "unavailable", "price": None, "reason": "Le scénario prudent dépasse les limites de calcul."}
            prudent_coefficient = monthly_mortgage_payment(1, prudent.inputs.annual_interest_rate, prudent.inputs.amortization_years)
            prudent_cash = prudent.financial.net_operating_income_annual / 12
            bounds.append((inputs.down_payment + (prudent_cash - threshold) / prudent_coefficient, CRITERIA[key][0]))
    if not bounds:
        return {"status": "unbounded", "price": None, "reason": "Vos critères ne définissent pas de plafond de prix."}
    price, binding = min(bounds)
    if price <= inputs.down_payment:
        return {"status": "infeasible", "price": None, "reason": "Aucun achat financé au-delà de votre mise de fonds ne respecte tous ces seuils avec les hypothèses actuelles."}
    return {"status": "available", "price": math.floor(price * 100) / 100, "binding_criterion": binding,
            "note": "Plafond de simulation avec mise de fonds, loyers, dépenses et coûts d’acquisition fixes. Ce n’est ni une valeur marchande, ni une qualification hypothécaire, ni un prix conseillé. Assurance hypothécaire et frais dépendant du prix non modélisés."}
