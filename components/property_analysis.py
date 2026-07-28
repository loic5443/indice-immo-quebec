"""User interface for a complete, mobile-friendly property analysis."""

import streamlit as st

from calculations.real_estate import AnalysisResult, PropertyInputs, calculate_analysis, validate_inputs
from components.account import current_user, is_authenticated
from components.immoengine import show_immoengine_result
from components.sidebar import go_to
from data.database import save_analysis
from domain.immoengine import PROFILE_WEIGHTS, evaluate_immoengine


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
    """Restore illustrative inputs without touching secrets or external data."""
    st.session_state.update(DEFAULTS)


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def _inputs_from_state() -> PropertyInputs:
    return PropertyInputs(
        price=st.session_state["property_price"], down_payment=st.session_state["down_payment"],
        annual_interest_rate=st.session_state["mortgage_rate"], amortization_years=st.session_state["amortization_years"],
        municipal_taxes_annual=st.session_state["municipal_taxes"], school_taxes_annual=st.session_state["school_taxes"],
        insurance_monthly=st.session_state["insurance"], condo_fees_monthly=st.session_state["condo_fees"],
        rental_income_monthly=st.session_state["rental_income"], other_expenses_monthly=st.session_state["other_expenses"],
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
    if is_authenticated():
        profile = current_user()["user_type"]
        st.caption(f"Profil ImmoEngine appliqué : {profile} (depuis Mon compte).")
    else:
        profile = st.selectbox("Profil ImmoEngine", list(PROFILE_WEIGHTS), key="analysis_engine_profile")
        st.caption("Créez un compte pour enregistrer votre profil et sauvegarder cette analyse.")
    _show_results(inputs, calculate_analysis(inputs), profile)


def _show_results(inputs: PropertyInputs, result: AnalysisResult, profile: str) -> None:
    st.subheader("Résultats de votre analyse")
    payment_col, expenses_col = st.columns(2)
    payment_col.metric("Paiement hypothécaire mensuel", _money(result.monthly_payment))
    payment_col.caption("Montant versé chaque mois pour rembourser le prêt.")
    expenses_col.metric("Dépenses mensuelles totales", _money(result.total_monthly_expenses))
    expenses_col.caption("Dépenses d'exploitation plus paiement hypothécaire.")

    cashflow_col, return_col = st.columns(2)
    cashflow_col.metric("Flux de trésorerie mensuel", _money(result.cash_flow_monthly))
    cashflow_col.caption("Loyers moins toutes les dépenses mensuelles, avant impôt.")
    return_col.metric("Rendement annuel sur la mise", f"{result.cash_on_cash_return:.2f} %")
    return_col.caption("Flux annuel avant impôt divisé par votre mise de fonds.")

    cap_col, dscr_col = st.columns(2)
    cap_col.metric("Taux de capitalisation", f"{result.capitalization_rate:.2f} %")
    cap_col.caption("RNE annuel divisé par le prix; il exclut le financement.")
    dscr_col.metric("Ratio de couverture de la dette", f"{result.debt_service_coverage_ratio:.2f}x")
    dscr_col.caption("Au-dessus de 1,00x, le RNE annuel couvre la dette.")

    if result.cash_flow_monthly >= 0:
        st.success("Le projet génère un flux de trésorerie mensuel positif avec les hypothèses saisies.")
    else:
        st.warning("Le flux de trésorerie est négatif : ajustez le prix, le financement, les revenus ou les dépenses.")

    engine_result = evaluate_immoengine(inputs, result, profile)
    show_immoengine_result(engine_result)

    st.markdown("<div class='save-analysis-panel'><h3>Sauvegarder cette analyse</h3>", unsafe_allow_html=True)
    if is_authenticated():
        property_name = st.text_input("Nom ou adresse de la propriété", key="saved_property_name", placeholder="Ex. Duplex – Montréal")
        if st.button("Sauvegarder dans Mes analyses", type="primary", key="save_analysis"):
            if not property_name.strip():
                st.error("Veuillez donner un nom ou une adresse à cette analyse.")
            else:
                save_analysis(
                    current_user()["id"],
                    property_name,
                    {
                        "price": inputs.price,
                        "down_payment": inputs.down_payment,
                        "rental_income": inputs.rental_income_monthly,
                        "monthly_expenses": result.total_monthly_expenses,
                        "cash_flow": result.cash_flow_monthly,
                        "cash_on_cash_return": result.cash_on_cash_return,
                        "capitalization_rate": result.capitalization_rate,
                        "debt_service_coverage_ratio": result.debt_service_coverage_ratio,
                    },
                    profile=engine_result.profile,
                    engine_result=engine_result,
                )
                st.success("Analyse sauvegardée dans Mes analyses.")
    else:
        st.write("Connectez-vous pour conserver cette analyse dans votre historique personnel.")
        st.button("Créer un compte ou se connecter", on_click=go_to, args=("Mon compte",), key="save_analysis_login")
    st.markdown("</div>", unsafe_allow_html=True)

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
            "Dépenses mensuelles totales": f"{_money(result.total_monthly_expenses)} par mois",
            "Revenu net d'exploitation (RNE)": f"{_money(result.net_operating_income_annual)} par année",
        }
        for label, value in rows.items():
            st.markdown(f"**{label}**  \n{value}")

    with explanations:
        st.subheader("Comment lire les résultats")
        st.write("**Paiement hypothécaire** — remboursement mensuel du prêt selon le taux et l'amortissement.")
        st.write("**Dépenses totales** — dépenses d'exploitation et remboursement hypothécaire réunis.")
        st.write("**Flux de trésorerie** — loyers moins dépenses d'exploitation et paiement hypothécaire, avant impôt.")
        st.write("**Rendement sur la mise** — flux annuel avant impôt divisé par votre mise de fonds.")
        st.write("**Taux de capitalisation** — revenu net d'exploitation annuel divisé par le prix; il exclut le financement.")
        st.write("**Couverture de la dette** — RNE annuel divisé par les versements hypothécaires annuels.")
        st.caption("Les résultats n'incluent pas l'impôt, les frais de notaire, les frais d'acquisition, la vacance, ni les rénovations majeures sauf si vous les ajoutez aux autres dépenses.")
