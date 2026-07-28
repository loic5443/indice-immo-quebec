"""Scenario and resilience presentation for the property analysis page."""

import streamlit as st

from domain.scenarios import build_resilience_tests, build_standard_scenarios


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def show_scenarios(inputs, profile) -> tuple[list[dict], dict]:
    """Render standard/custom scenarios and return serializable snapshots."""
    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>SIMULATEUR « ET SI? »</p><h2>Comparez vos hypothèses, sans confondre un scénario avec une prévision.</h2>", unsafe_allow_html=True)
    custom = None
    with st.expander("Créer un scénario personnalisé", expanded=False):
        first, second, third = st.columns(3)
        with first:
            price = st.number_input("Prix personnalisé ($)", min_value=1.0, value=float(inputs.price), step=5_000.0)
            down_payment = st.number_input("Mise de fonds personnalisée ($)", min_value=1.0, value=float(inputs.down_payment), step=5_000.0)
            rate = st.number_input("Taux personnalisé (%)", min_value=0.0, max_value=25.0, value=float(inputs.annual_interest_rate), step=0.05)
        with second:
            rental_income = st.number_input("Revenus locatifs personnalisés ($/mois)", min_value=0.0, value=float(inputs.rental_income_monthly), step=100.0)
            vacancy = st.number_input("Vacance personnalisée (%)", min_value=0.0, max_value=100.0, value=float(inputs.vacancy_rate_pct), step=0.5)
            expense_multiplier = st.number_input("Multiplicateur des dépenses", min_value=0.5, max_value=2.0, value=1.0, step=0.05)
        with third:
            repairs = st.number_input("Travaux initiaux personnalisés ($)", min_value=0.0, value=float(inputs.initial_repairs), step=1_000.0)
            horizon = st.number_input("Horizon personnalisé (années)", min_value=1, max_value=40, value=int(inputs.holding_period_years), step=1)
            include_custom = st.checkbox("Inclure ce scénario", value=False)
        if include_custom:
            custom = {
                "price": price, "down_payment": down_payment, "annual_interest_rate": rate,
                "rental_income_monthly": rental_income, "vacancy_rate_pct": vacancy,
                "expense_multiplier": expense_multiplier, "initial_repairs": repairs,
                "holding_period_years": horizon,
            }
    if custom and custom["down_payment"] >= custom["price"]:
        st.error("Dans le scénario personnalisé, la mise de fonds doit être inférieure au prix.")
        custom = None
    scenarios = build_standard_scenarios(inputs, profile, custom)
    rows = []
    base = next(item for item in scenarios if item.name == "Scénario de base")
    for scenario in scenarios:
        financial = scenario.financial
        rows.append({
            "Scénario": scenario.name,
            "Paiement": _money(financial.monthly_payment),
            "RNE annuel": _money(financial.net_operating_income_annual),
            "Flux mensuel": _money(financial.cash_flow_monthly),
            "Rendement capital": f"{financial.cash_on_cash_return:.2f} %",
            "Capitalisation": f"{financial.capitalization_rate:.2f} %",
            "DSCR": f"{financial.debt_service_coverage_ratio:.2f}x",
            "Écart flux/base": _money(financial.cash_flow_monthly - base.financial.cash_flow_monthly),
            "Score": f"{scenario.engine.score:.0f} / 100" if scenario.engine.score is not None else "Indisponible",
            "Écart score/base": f"{(scenario.engine.score or 0) - (base.engine.score or 0):+.0f}",
            "Verdict": scenario.engine.verdict,
            "Confiance": f"{scenario.engine.confidence_index} / 100",
        })
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Les écarts montrent la sensibilité aux hypothèses. Le scénario favorable n'est pas une prévision.")
    st.write(f"Écart de flux prudent/base : {_money(scenarios[0].financial.cash_flow_monthly - base.financial.cash_flow_monthly)} par mois.")

    st.markdown("<p class='eyebrow'>TESTS DE RÉSISTANCE</p><h2>Comment votre projet réagit aux chocs simples.</h2>", unsafe_allow_html=True)
    resilience_tests, status = build_resilience_tests(inputs, profile)
    resilience_rows = [{
        "Test": item.name,
        "Flux mensuel": _money(item.financial.cash_flow_monthly),
        "DSCR": f"{item.financial.debt_service_coverage_ratio:.2f}x",
        "Verdict": item.engine.verdict,
    } for item in resilience_tests]
    st.dataframe(resilience_rows, hide_index=True, width="stretch")
    st.markdown(f"**Synthèse de résistance :** {status.capitalize()}")
    st.caption("Résistant : tous les tests gardent un flux >= 0 $ et un DSCR >= 1,10x. Sensible : le test combiné garde un flux >= 0 $ et un DSCR >= 1,00x. Fragile : autrement. Données insuffisantes : score indisponible dans un test.")
    return [item.to_snapshot() for item in scenarios], {"status": status, "tests": [item.to_snapshot() for item in resilience_tests]}
