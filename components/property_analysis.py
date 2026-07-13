"""User interface for a complete, mobile-friendly property analysis."""

import streamlit as st

from calculations.real_estate import AnalysisResult, PropertyInputs, calculate_analysis, validate_inputs


DEFAULTS = {
    "property_price": 450_000.0,
    "down_payment": 90_000.0,
    "mortgage_rate": 4.75,
    "amortization_years": 25,
    "municipal_taxes": 3_600.0,
    "school_taxes": 400.0,
    "insurance": 125.0,
    "condo_fees": 0.0,
    "rental_income": 2_600.0,
    "other_expenses": 250.0,
}


def reset_analysis() -> None:
    """Restore safe, illustrative inputs without touching secrets or external data."""
    st.session_state.update(DEFAULTS)


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def _inputs_from_state() -> PropertyInputs:
    return PropertyInputs(
        price=st.session_state["property_price"],
        down_payment=st.session_state["down_payment"],
        annual_interest_rate=st.session_state["mortgage_rate"],
        amortization_years=st.session_state["amortization_years"],
        municipal_taxes_annual=st.session_state["municipal_taxes"],
        school_taxes_annual=st.session_state["school_taxes"],
        insurance_monthly=st.session_state["insurance"],
        condo_fees_monthly=st.session_state["condo_fees"],
        rental_income_monthly=st.session_state["rental_income"],
        other_expenses_monthly=st.session_state["other_expenses"],
    )


def show_property_analysis() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.title("Analyse immobilière")
    st.write("Saisissez vos hypothèses pour mesurer la viabilité d'un achat locatif. Les résultats sont indicatifs et avant impôt.")
    st.button("Réinitialiser l'analyse", on_click=reset_analysis, type="secondary")

    with st.expander("Hypothèses de financement et d'exploitation", expanded=True):
        acquisition, financement = st.columns(2)
        with acquisition:
            st.number_input("Prix de la propriété ($)", min_value=0.0, step=5_000.0, key="property_price")
            st.number_input("Mise de fonds ($)", min_value=0.0, step=5_000.0, key="down_payment")
            st.number_input("Taxes municipales annuelles ($)", min_value=0.0, step=100.0, key="municipal_taxes")
            st.number_input("Taxes scolaires annuelles ($)", min_value=0.0, step=50.0, key="school_taxes")
        with financement:
            st.number_input("Taux hypothécaire annuel (%)", min_value=0.0, max_value=25.0, step=0.05, format="%.2f", key="mortgage_rate")
            st.number_input("Amortissement (années)", min_value=5, max_value=30, step=1, key="amortization_years")
            st.number_input("Assurances mensuelles ($)", min_value=0.0, step=25.0, key="insurance")
            st.number_input("Frais de copropriété mensuels ($)", min_value=0.0, step=25.0, key="condo_fees")

        revenus, depenses = st.columns(2)
        with revenus:
            st.number_input("Revenus locatifs mensuels ($)", min_value=0.0, step=100.0, key="rental_income")
        with depenses:
            st.number_input("Autres dépenses mensuelles ($)", min_value=0.0, step=25.0, key="other_expenses", help="Entretien, services, gestion ou réserve, selon votre projet.")

    inputs = _inputs_from_state()
    errors = validate_inputs(inputs)
    if errors:
        for error in errors:
            st.error(error)
        st.info("Corrigez les champs indiqués pour obtenir une analyse fiable.")
        return

    result = calculate_analysis(inputs)
    _show_results(inputs, result)


def _show_results(inputs: PropertyInputs, result: AnalysisResult) -> None:
    st.subheader("Résultats de votre analyse")
    payment_col, cashflow_col, return_col, dscr_col = st.columns(4)
    payment_col.metric("Paiement hypothécaire mensuel", _money(result.monthly_payment))
    cashflow_col.metric("Flux de trésorerie mensuel", _money(result.cash_flow_monthly))
    return_col.metric("Rendement sur la mise", f"{result.cash_on_cash_return:.2f} %")
    dscr_col.metric("Couverture de la dette", f"{result.debt_service_coverage_ratio:.2f}x")

    if result.cash_flow_monthly >= 0:
        st.success("Le projet génère un flux de trésorerie mensuel positif avec les hypothèses saisies.")
    else:
        st.warning("Le flux de trésorerie est négatif : ajustez le prix, le financement, les revenus ou les dépenses.")

    details, explanations = st.columns([1.1, 1])
    with details:
        st.subheader("Fiche d'analyse")
        rows = {
            "Prix de la propriété": _money(inputs.price),
            "Mise de fonds": _money(inputs.down_payment),
            "Montant financé": _money(result.loan_amount),
            "Taux / amortissement": f"{inputs.annual_interest_rate:.2f} % / {inputs.amortization_years} ans",
            "Taxes municipales / scolaires": f"{_money(inputs.municipal_taxes_annual)} / {_money(inputs.school_taxes_annual)} par année",
            "Assurances / copropriété": f"{_money(inputs.insurance_monthly)} / {_money(inputs.condo_fees_monthly)} par mois",
            "Revenus locatifs": f"{_money(inputs.rental_income_monthly)} par mois",
            "Dépenses d'exploitation": f"{_money(result.operating_expenses_monthly)} par mois",
            "Revenu net d'exploitation (RNE)": f"{_money(result.net_operating_income_annual)} par année",
            "Taux de capitalisation": f"{result.capitalization_rate:.2f} %",
        }
        for label, value in rows.items():
            st.write(f"**{label}**  \\n+{value}")

    with explanations:
        st.subheader("Comment lire les résultats")
        st.write("**Paiement hypothécaire** — remboursement mensuel du prêt selon le taux et l'amortissement.")
        st.write("**Flux de trésorerie** — loyers moins dépenses d'exploitation et paiement hypothécaire, avant impôt.")
        st.write("**Rendement sur la mise** — flux annuel avant impôt divisé par votre mise de fonds. Il mesure le rendement de votre argent investi.")
        st.write("**Taux de capitalisation** — revenu net d'exploitation annuel divisé par le prix. Il exclut le financement.")
        st.write("**Ratio de couverture de la dette** — RNE annuel divisé par les versements hypothécaires annuels. Au-dessus de 1,00x, le RNE couvre la dette.")
        st.caption("Les résultats n'incluent pas l'impôt, les frais de notaire, les frais d'acquisition, la vacance, ni les rénovations majeures sauf si vous les ajoutez aux autres dépenses.")
