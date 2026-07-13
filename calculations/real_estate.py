"""Recognized, transparent real-estate investment calculations."""

from dataclasses import dataclass


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


@dataclass(frozen=True)
class AnalysisResult:
    loan_amount: float
    monthly_payment: float
    operating_expenses_monthly: float
    net_operating_income_annual: float
    cash_flow_monthly: float
    cash_on_cash_return: float
    capitalization_rate: float
    debt_service_coverage_ratio: float


def validate_inputs(inputs: PropertyInputs) -> list[str]:
    """Return user-facing validation messages for impossible assumptions."""
    errors = []
    if inputs.price <= 0:
        errors.append("Le prix de la propriété doit être supérieur à 0 $.")
    if inputs.down_payment <= 0:
        errors.append("La mise de fonds doit être supérieure à 0 $ pour calculer le rendement sur la mise.")
    if inputs.down_payment >= inputs.price:
        errors.append("La mise de fonds doit être inférieure au prix de la propriété.")
    if not 0 <= inputs.annual_interest_rate <= 25:
        errors.append("Le taux hypothécaire doit être compris entre 0 % et 25 %.")
    if not 5 <= inputs.amortization_years <= 30:
        errors.append("L'amortissement doit être compris entre 5 et 30 ans.")

    non_negative = {
        "Les taxes municipales": inputs.municipal_taxes_annual,
        "Les taxes scolaires": inputs.school_taxes_annual,
        "Les assurances": inputs.insurance_monthly,
        "Les frais de copropriété": inputs.condo_fees_monthly,
        "Les revenus locatifs": inputs.rental_income_monthly,
        "Les autres dépenses": inputs.other_expenses_monthly,
    }
    errors.extend(f"{label} ne peuvent pas être négatifs." for label, value in non_negative.items() if value < 0)
    return errors


def monthly_mortgage_payment(loan_amount: float, annual_interest_rate: float, amortization_years: int) -> float:
    """Calculate a fixed monthly payment using the standard amortizing-loan formula."""
    months = amortization_years * 12
    # Canadian fixed mortgage quotes are conventionally compounded twice a year.
    # Convert that quoted annual rate to its equivalent monthly rate before amortizing.
    monthly_rate = (1 + annual_interest_rate / 100 / 2) ** (2 / 12) - 1
    if monthly_rate == 0:
        return loan_amount / months
    # M = P * r(1+r)^n / ((1+r)^n - 1), where P is the loan, r the monthly rate and n months.
    return loan_amount * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)


def calculate_analysis(inputs: PropertyInputs) -> AnalysisResult:
    """Calculate operating income, cash flow and investment ratios from validated inputs."""
    errors = validate_inputs(inputs)
    if errors:
        raise ValueError(" ".join(errors))

    loan_amount = inputs.price - inputs.down_payment
    monthly_payment = monthly_mortgage_payment(loan_amount, inputs.annual_interest_rate, inputs.amortization_years)
    operating_expenses_monthly = (
        inputs.municipal_taxes_annual / 12
        + inputs.school_taxes_annual / 12
        + inputs.insurance_monthly
        + inputs.condo_fees_monthly
        + inputs.other_expenses_monthly
    )
    net_operating_income_annual = (inputs.rental_income_monthly - operating_expenses_monthly) * 12
    cash_flow_monthly = inputs.rental_income_monthly - operating_expenses_monthly - monthly_payment
    # Cash-on-cash return uses annual pre-tax cash flow divided by the cash invested (down payment).
    cash_on_cash_return = cash_flow_monthly * 12 / inputs.down_payment * 100
    capitalization_rate = net_operating_income_annual / inputs.price * 100
    annual_debt_service = monthly_payment * 12
    debt_service_coverage_ratio = net_operating_income_annual / annual_debt_service

    return AnalysisResult(
        loan_amount=loan_amount,
        monthly_payment=monthly_payment,
        operating_expenses_monthly=operating_expenses_monthly,
        net_operating_income_annual=net_operating_income_annual,
        cash_flow_monthly=cash_flow_monthly,
        cash_on_cash_return=cash_on_cash_return,
        capitalization_rate=capitalization_rate,
        debt_service_coverage_ratio=debt_service_coverage_ratio,
    )
