"""Market context page, explicitly separating live and simulated information."""

import streamlit as st

from components.charts import show_market_chart
from data.real_data import get_canada_policy_rate
from data.simulated_data import SIMULATED_INFLATION, SIMULATED_UNEMPLOYMENT


def show_markets() -> None:
    st.title("Marchés")
    st.write("Des repères pour situer votre projet. Les tendances locales affichées sont actuellement des exemples de présentation.")
    rate, is_live = get_canada_policy_rate()
    one, two, three = st.columns(3)
    one.metric("Taux directeur du Canada", f"{rate:.2f} %", "Donnée réelle" if is_live else "Valeur de repli")
    two.metric("Inflation", f"{SIMULATED_INFLATION:.1f} %", "Donnée simulée")
    three.metric("Chômage", f"{SIMULATED_UNEMPLOYMENT:.1f} %", "Donnée simulée")
    st.info("Les prix, variations et historiques par ville ci-dessous sont simulés. Ils ne remplacent pas une étude de marché locale vérifiée.")
    show_market_chart("Montréal")
