"""Existing Brevo alert interface, kept separate from navigation and page layout."""

import json

import requests
import streamlit as st


def show_alert_signup() -> None:
    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    st.subheader("Restez informé")
    st.write("Recevez une notification lorsque les indicateurs suivis évoluent.")
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
                    data=json.dumps({"email": email, "updateEnabled": True}), timeout=10,
                )
                if response.status_code in {200, 201, 204}:
                    st.success("Adresse courriel enregistrée avec succès.")
                else:
                    st.error("Impossible d'enregistrer l'adresse pour le moment.")
            except requests.RequestException:
                st.error("Le service d'alertes est temporairement inaccessible.")
