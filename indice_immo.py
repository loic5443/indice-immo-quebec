"""ImmoRadar entry point: UI composition only; calculations live in calculations/."""

import json

import requests
import streamlit as st

from components.charts import show_market_chart
from components.header import show_header
from components.premium import show_premium
from components.property_analysis import show_property_analysis
from components.sidebar import show_sidebar
from data.real_data import get_canada_policy_rate
from data.simulated_data import SIMULATED_INFLATION, SIMULATED_UNEMPLOYMENT


st.set_page_config(page_title="ImmoRadar", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

with open("styles/main.css", encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

page = show_sidebar()

if page == "Analyse immobilière":
    show_property_analysis()
    st.stop()

if page == "Premium":
    show_premium()
    st.stop()

show_header()
policy_rate, policy_rate_is_live = get_canada_policy_rate()
st.subheader("Repères de marché")
rate_col, inflation_col, unemployment_col = st.columns(3)
rate_col.metric("Taux directeur du Canada", f"{policy_rate:.2f} %", "Donnée réelle" if policy_rate_is_live else "Valeur de repli simulée")
inflation_col.metric("Inflation", f"{SIMULATED_INFLATION:.1f} %", "Donnée simulée")
unemployment_col.metric("Chômage", f"{SIMULATED_UNEMPLOYMENT:.1f} %", "Donnée simulée")

st.caption("Les statistiques de villes et les indicateurs simulés sont séparés des calculs financiers. Ouvrez « Analyse immobilière » pour entrer les données réelles de votre projet.")
show_market_chart("Montréal")

st.divider()
st.subheader("Alertes ImmoRadar")
st.write("Recevez une notification lorsque les indicateurs suivis évoluent. Cette fonction utilise uniquement la configuration Brevo déjà présente, si elle existe.")
email = st.text_input("Votre adresse courriel", placeholder="vous@exemple.com")
if st.button("Recevoir les alertes"):
    if not email or "@" not in email:
        st.error("Veuillez saisir une adresse courriel valide.")
    elif "BREVO_API_KEY" not in st.secrets:
        st.info("Les alertes ne sont pas configurées dans cette version. Aucune adresse n'a été envoyée.")
    else:
        try:
            response = requests.post(
                "https://api.brevo.com/v3/contacts",
                headers={"accept": "application/json", "api-key": st.secrets["BREVO_API_KEY"], "content-type": "application/json"},
                data=json.dumps({"email": email, "updateEnabled": True}),
                timeout=10,
            )
            if response.status_code in {200, 201, 204}:
                st.success("Adresse courriel enregistrée avec succès.")
            else:
                st.error("Impossible d'enregistrer l'adresse pour le moment.")
        except requests.RequestException:
            st.error("Le service d'alertes est temporairement inaccessible.")
