"""Premium-only alerts preview; no real alerts or contact data are collected in beta."""
import streamlit as st
from components.sidebar import go_to
def show_alert_signup() -> None:
    st.markdown("<div class='premium-notice'><p class='eyebrow notranslate'>ALERTES PREMIUM</p><h2>Ne manquez plus les changements qui comptent.</h2><p>Suivez vos propriétés et marchés favoris grâce aux alertes personnalisées ImmoRadar. Aperçu d'interface seulement : aucun envoi n'est actif pendant la bêta.</p></div>",unsafe_allow_html=True)
    st.button("Découvrir Premium",on_click=go_to,args=("Premium",),key="alerts_premium")
