"""Complete property analysis UI with enriched assumptions and deterministic scenarios."""

from dataclasses import asdict

import streamlit as st

from calculations.real_estate import AnalysisResult, PropertyInputs, calculate_analysis, validate_inputs
from components.account import current_user, is_authenticated
from components.immoengine import show_immoengine_result
from components.scenarios import show_scenarios
from components.sidebar import go_to
from data.database import save_analysis
from domain.immoengine import PROFILE_WEIGHTS, evaluate_immoengine


DEFAULTS = {
    "property_price": 450_000.0, "down_payment": 90_000.0, "mortgage_rate": 4.75,
    "amortization_years": 25, "municipal_taxes": 3_600.0, "school_taxes": 400.0,
    "insurance": 125.0, "condo_fees": 0.0, "rental_income": 2_600.0,
    "other_expenses": 250.0, "household_income": 0.0, "other_debts": 0.0,
    "vacancy_rate": 3.0, "maintenance": 100.0, "management": 0.0,
    "utilities": 0.0, "capital_reserve": 100.0, "initial_repairs": 0.0,
    "acquisition_costs": 0.0, "other_income": 0.0, "rent_growth": 2.0,
    "expense_growth": 2.0, "holding_period": 5,
}


def reset_analysis() -> None:
    st.session_state.update(DEFAULTS)


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def _inputs_from_state() -> PropertyInputs:
    household_income = st.session_state["household_income"] or None
    return PropertyInputs(
        price=st.session_state["property_price"], down_payment=st.session_state["down_payment"],
        annual_interest_rate=st.session_state["mortgage_rate"], amortization_years=st.session_state["amortization_years"],
        municipal_taxes_annual=st.session_state["municipal_taxes"], school_taxes_annual=st.session_state["school_taxes"],
        insurance_monthly=st.session_state["insurance"], condo_fees_monthly=st.session_state["condo_fees"],
        rental_income_monthly=st.session_state["rental_income"], other_expenses_monthly=st.session_state["other_expenses"],
        household_income_annual=household_income, other_debt_payments_monthly=st.session_state["other_debts"],
        vacancy_rate_pct=st.session_state["vacancy_rate"], maintenance_monthly=st.session_state["maintenance"],
        management_monthly=st.session_state["management"], owner_paid_utilities_monthly=st.session_state["utilities"],
        capital_reserve_monthly=st.session_state["capital_reserve"], initial_repairs=st.session_state["initial_repairs"],
        acquisition_costs=st.session_state["acquisition_costs"], other_income_monthly=st.session_state["other_income"],
        rent_growth_annual_pct=st.session_state["rent_growth"], expense_growth_annual_pct=st.session_state["expense_growth"],
        holding_period_years=st.session_state["holding_period"],
    )


def show_property_analysis() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.title("Analyse immobilière")
    st.write("Saisissez vos hypothèses. Les résultats sont indicatifs, déterministes et avant impôt; ils ne constituent pas une évaluation officielle.")
    st.button("Réinitialiser l'analyse", on_click=reset_analysis, type="secondary")

    with st.expander("Acquisition et financement", expanded=True):
        acquisition, financing = st.columns(2)
        with acquisition:
            st.number_input("Prix de la propriété ($)", min_value=0.0, step=5_000.0, key="property_price")
            st.number_input("Mise de fonds ($)", min_value=0.0, step=5_000.0, key="down_payment")
            st.number_input("Travaux initiaux ($)", min_value=0.0, step=1_000.0, key="initial_repairs")
            st.number_input("Frais d'acquisition ($)", min_value=0.0, step=1_000.0, key="acquisition_costs")
        with financing:
            st.number_input("Taux hypothécaire annuel (%)", min_value=0.0, max_value=25.0, step=0.05, format="%.2f", key="mortgage_rate")
            st.number_input("Amortissement (années)", min_value=5, max_value=30, step=1, key="amortization_years")
            st.number_input("Revenu brut annuel du ménage ($, facultatif)", min_value=0.0, step=5_000.0, key="household_income")
            st.number_input("Autres dettes mensuelles ($, facultatif)", min_value=0.0, step=100.0, key="other_debts")

    with st.expander("Revenus et dépenses d'exploitation", expanded=True):
        revenue, monthly, annual = st.columns(3)
        with revenue:
            st.number_input("Revenus locatifs mensuels ($)", min_value=0.0, step=100.0, key="rental_income")
            st.number_input("Autres revenus mensuels ($)", min_value=0.0, step=50.0, key="other_income")
            st.number_input("Taux de vacance (%)", min_value=0.0, max_value=100.0, step=0.5, key="vacancy_rate")
        with monthly:
            st.number_input("Assurances mensuelles ($)", min_value=0.0, step=25.0, key="insurance")
            st.number_input("Frais de copropriété mensuels ($)", min_value=0.0, step=25.0, key="condo_fees")
            st.number_input("Entretien courant mensuel ($)", min_value=0.0, step=25.0, key="maintenance")
            st.number_input("Frais de gestion mensuels ($)", min_value=0.0, step=25.0, key="management")
            st.number_input("Services publics mensuels ($)", min_value=0.0, step=25.0, key="utilities")
            st.number_input("Réserve mensuelle dépenses majeures ($)", min_value=0.0, step=25.0, key="capital_reserve")
            st.number_input("Autres dépenses mensuelles ($)", min_value=0.0, step=25.0, key="other_expenses")
        with annual:
            st.number_input("Taxes municipales annuelles ($)", min_value=0.0, step=100.0, key="municipal_taxes")
            st.number_input("Taxes scolaires annuelles ($)", min_value=0.0, step=50.0, key="school_taxes")

    with st.expander("Hypothèses de projection", expanded=False):
        growth, horizon = st.columns(2)
        with growth:
            st.number_input("Croissance annuelle hypothétique des loyers (%)", min_value=-25.0, max_value=25.0, step=0.25, key="rent_growth")
            st.number_input("Croissance annuelle hypothétique des dépenses (%)", min_value=-25.0, max_value=25.0, step=0.25, key="expense_growth")
        with horizon:
            st.number_input("Horizon de détention (années)", min_value=1, max_value=40, step=1, key="holding_period")
        st.caption("Ces projections utilisent uniquement vos taux de croissance déclarés. Elles ne prévoient pas le marché ni la valeur future de la propriété.")

    inputs = _inputs_from_state()
    errors = validate_inputs(inputs)
    if errors:
        for error in errors:
            st.error(error)
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
    first, second, third = st.columns(3)
    first.metric("Paiement hypothécaire", _money(result.monthly_payment))
    second.metric("Revenus effectifs mensuels", _money(result.effective_rental_income_monthly))
    third.metric("Flux de trésorerie mensuel", _money(result.cash_flow_monthly))
    a, b, c = st.columns(3)
    a.metric("RNE annuel", _money(result.net_operating_income_annual))
    b.metric("Capital réellement investi", _money(result.actual_capital_invested))
    c.metric("Rendement sur capital", f"{result.cash_on_cash_return:.2f} %")
    d, e, f = st.columns(3)
    d.metric("Taux de capitalisation", f"{result.capitalization_rate:.2f} %")
    e.metric("DSCR", f"{result.debt_service_coverage_ratio:.2f}x")
    f.metric("Marge mensuelle de sécurité", _money(result.monthly_safety_margin))
    if result.housing_cost_ratio is not None:
        st.info(f"Ratio déclaré des coûts de logement et autres dettes : {result.housing_cost_ratio:.1f} %. Méthode : (paiement hypothécaire + dépenses d'exploitation + autres dettes) / revenu brut mensuel. Ce n'est pas un critère officiel de prêteur.")
    else:
        st.caption("Abordabilité indisponible : ajoutez le revenu brut annuel du ménage pour calculer le ratio déclaré des coûts de logement.")
    st.caption(f"Projection à {inputs.holding_period_years} ans : flux mensuel hypothétique {_money(result.projected_cash_flow_monthly)}, fondé seulement sur les croissances de loyers et dépenses saisies.")

    engine_result = evaluate_immoengine(inputs, result, profile)
    show_immoengine_result(engine_result)
    scenarios, resilience = show_scenarios(inputs, engine_result.profile)

    st.markdown("<div class='save-analysis-panel'><h3>Sauvegarder cette analyse</h3>", unsafe_allow_html=True)
    if is_authenticated():
        property_name = st.text_input("Nom ou adresse de la propriété", key="saved_property_name", placeholder="Ex. Duplex - Montréal")
        if st.button("Sauvegarder dans Mes analyses", type="primary", key="save_analysis"):
            if not property_name.strip():
                st.error("Veuillez donner un nom ou une adresse à cette analyse.")
            else:
                save_analysis(current_user()["id"], property_name, {
                    "price": inputs.price, "down_payment": inputs.down_payment,
                    "rental_income": inputs.rental_income_monthly, "monthly_expenses": result.total_monthly_expenses,
                    "cash_flow": result.cash_flow_monthly, "cash_on_cash_return": result.cash_on_cash_return,
                    "capitalization_rate": result.capitalization_rate,
                    "debt_service_coverage_ratio": result.debt_service_coverage_ratio,
                    "financial_inputs": asdict(inputs), "scenarios": scenarios, "resilience": resilience,
                }, profile=engine_result.profile, engine_result=engine_result)
                st.success("Analyse, scénarios et tests de résistance sauvegardés dans Mes analyses.")
    else:
        st.write("Connectez-vous pour conserver cette analyse, ses scénarios et ses tests de résistance.")
        st.button("Créer un compte ou se connecter", on_click=go_to, args=("Mon compte",), key="save_analysis_login")
    st.markdown("</div>", unsafe_allow_html=True)
