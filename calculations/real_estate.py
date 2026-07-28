"""Deterministic Canadian real-estate calculations from stated assumptions only."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PropertyInputs:
    price: float
    down_payment: float
    annual_interest_rate: float
    amortization_years: int
    municipal_taxes_annual: float
    school_taxes_annual: float
    insurance_monthly: float
    condo_fees_monthly: float
    rental_income_monthly: float
    other_expenses_monthly: float
    household_income_annual: Optional[float] = None
    other_debt_payments_monthly: float = 0.0
    vacancy_rate_pct: float = 0.0
    maintenance_monthly: float = 0.0
    management_monthly: float = 0.0
    owner_paid_utilities_monthly: float = 0.0
    capital_reserve_monthly: float = 0.0
    initial_repairs: float = 0.0
    acquisition_costs: float = 0.0
    other_income_monthly: float = 0.0
    rent_growth_annual_pct: float = 0.0
    expense_growth_annual_pct: float = 0.0
    holding_period_years: int = 5


@dataclass(frozen=True)
class AnalysisResult:
    loan_amount: float
    monthly_payment: float
    operating_expenses_monthly: float
    total_monthly_expenses: float
    net_operating_income_annual: float
    cash_flow_monthly: float
    cash_on_cash_return: float
    capitalization_rate: float
    debt_service_coverage_ratio: float
    gross_rental_income_monthly: float
    effective_rental_income_monthly: float
    annual_debt_service: float
    actual_capital_invested: float
    housing_cost_ratio: Optional[float]
    monthly_safety_margin: float
    projected_cash_flow_monthly: float


def validate_inputs(inputs: PropertyInputs) -> list[str]:
    """Return user-facing validation messages for impossible assumptions."""
    errors = []
    if inputs.price <= 0:
        errors.append("Le prix de la propriété doit être supérieur à 0 $.")
    if inputs.down_payment <= 0:
        errors.append("La mise de fonds doit être supérieure à 0 $ pour calculer le rendement sur le capital investi.")
    if inputs.down_payment >= inputs.price:
        errors.append("La mise de fonds doit être inférieure au prix de la propriété.")
    if not 0 <= inputs.annual_interest_rate <= 25:
        errors.append("Le taux hypothécaire doit être compris entre 0 % et 25 %.")
    if not 5 <= inputs.amortization_years <= 30:
        errors.append("L'amortissement doit être compris entre 5 et 30 ans.")
    if not 0 <= inputs.vacancy_rate_pct <= 100:
        errors.append("Le taux de vacance doit être compris entre 0 % et 100 %.")
    if not -25 <= inputs.rent_growth_annual_pct <= 25 or not -25 <= inputs.expense_growth_annual_pct <= 25:
        errors.append("Les hypothèses de croissance annuelle doivent être comprises entre -25 % et 25 %.")
    if not 1 <= inputs.holding_period_years <= 40:
        errors.append("L'horizon de détention doit être compris entre 1 et 40 ans.")
    if inputs.household_income_annual is not None and inputs.household_income_annual <= 0:
        errors.append("Le revenu brut annuel du ménage doit être supérieur à 0 $ lorsqu'il est renseigné.")

    non_negative = {
        "Les taxes municipales": inputs.municipal_taxes_annual,
        "Les taxes scolaires": inputs.school_taxes_annual,
        "Les assurances": inputs.insurance_monthly,
        "Les frais de copropriété": inputs.condo_fees_monthly,
        "Les revenus locatifs": inputs.rental_income_monthly,
        "Les autres dépenses": inputs.other_expenses_monthly,
        "Les autres dettes": inputs.other_debt_payments_monthly,
        "L'entretien courant": inputs.maintenance_monthly,
        "Les frais de gestion": inputs.management_monthly,
        "Les services publics": inputs.owner_paid_utilities_monthly,
        "La réserve pour dépenses majeures": inputs.capital_reserve_monthly,
        "Les travaux initiaux": inputs.initial_repairs,
        "Les frais d'acquisition": inputs.acquisition_costs,
        "Les autres revenus": inputs.other_income_monthly,
    }
    errors.extend(f"{label} ne peuvent pas être négatifs." for label, value in non_negative.items() if value < 0)
    return errors


def monthly_mortgage_payment(loan_amount: float, annual_interest_rate: float, amortization_years: int) -> float:
    """Calculate a fixed monthly payment using the Canadian semi-annual convention."""
    months = amortization_years * 12
    monthly_rate = (1 + annual_interest_rate / 100 / 2) ** (2 / 12) - 1
    if monthly_rate == 0:
        return loan_amount / months
    return loan_amount * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)


def calculate_analysis(inputs: PropertyInputs) -> AnalysisResult:
    """Calculate income, operating costs, financing and projection assumptions.

    Net operating income excludes debt service by definition. All outputs remain
    deterministic and are based exclusively on user-entered assumptions.
    """
    errors = validate_inputs(inputs)
    if errors:
        raise ValueError(" ".join(errors))

    loan_amount = inputs.price - inputs.down_payment
    monthly_payment = monthly_mortgage_payment(loan_amount, inputs.annual_interest_rate, inputs.amortization_years)
    gross_rental_income_monthly = inputs.rental_income_monthly + inputs.other_income_monthly
    effective_rental_income_monthly = (
        inputs.rental_income_monthly * (1 - inputs.vacancy_rate_pct / 100) + inputs.other_income_monthly
    )
    operating_expenses_monthly = (
        inputs.municipal_taxes_annual / 12 + inputs.school_taxes_annual / 12
        + inputs.insurance_monthly + inputs.condo_fees_monthly + inputs.other_expenses_monthly
        + inputs.maintenance_monthly + inputs.management_monthly + inputs.owner_paid_utilities_monthly
        + inputs.capital_reserve_monthly
    )
    # Debt service is intentionally excluded from NOI/RNE.
    net_operating_income_annual = (effective_rental_income_monthly - operating_expenses_monthly) * 12
    annual_debt_service = monthly_payment * 12
    total_monthly_expenses = operating_expenses_monthly + monthly_payment
    cash_flow_monthly = effective_rental_income_monthly - total_monthly_expenses
    actual_capital_invested = inputs.down_payment + inputs.initial_repairs + inputs.acquisition_costs
    cash_on_cash_return = cash_flow_monthly * 12 / actual_capital_invested * 100
    capitalization_rate = net_operating_income_annual / inputs.price * 100
    debt_service_coverage_ratio = net_operating_income_annual / annual_debt_service if annual_debt_service else 0.0
    housing_cost_ratio = None
    if inputs.household_income_annual is not None:
        housing_cost_ratio = (
            total_monthly_expenses + inputs.other_debt_payments_monthly
        ) / (inputs.household_income_annual / 12) * 100
    future_income = effective_rental_income_monthly * (1 + inputs.rent_growth_annual_pct / 100) ** inputs.holding_period_years
    future_expenses = operating_expenses_monthly * (1 + inputs.expense_growth_annual_pct / 100) ** inputs.holding_period_years
    projected_cash_flow_monthly = future_income - future_expenses - monthly_payment

    return AnalysisResult(
        loan_amount=loan_amount, monthly_payment=monthly_payment,
        operating_expenses_monthly=operating_expenses_monthly,
        total_monthly_expenses=total_monthly_expenses,
        net_operating_income_annual=net_operating_income_annual,
        cash_flow_monthly=cash_flow_monthly,
        cash_on_cash_return=cash_on_cash_return,
        capitalization_rate=capitalization_rate,
        debt_service_coverage_ratio=debt_service_coverage_ratio,
        gross_rental_income_monthly=gross_rental_income_monthly,
        effective_rental_income_monthly=effective_rental_income_monthly,
        annual_debt_service=annual_debt_service,
        actual_capital_invested=actual_capital_invested,
        housing_cost_ratio=housing_cost_ratio,
        monthly_safety_margin=cash_flow_monthly,
        projected_cash_flow_monthly=projected_cash_flow_monthly,
    )
