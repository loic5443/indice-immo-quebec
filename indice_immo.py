"""ImmoRadar entry point: page composition only."""

from pathlib import Path

import streamlit as st

from components.about import show_about
from components.admin import show_admin
from components.feedback import show_feedback
from components.account import initialize_session, show_account
from components.home import show_home
from components.markets import show_markets
from components.premium import show_premium
from components.privacy import show_privacy
from components.property_analysis import show_property_analysis
from components.saved_analyses import show_saved_analyses
from components.sidebar import show_sidebar
from data.database import initialize_database


st.set_page_config(page_title="ImmoRadar", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<script>document.documentElement.lang='fr-CA';document.documentElement.setAttribute('translate','no');</script><meta http-equiv='content-language' content='fr-CA'>", unsafe_allow_html=True)

initialize_database()
initialize_session()

css_path = Path(__file__).resolve().parent / "styles" / "main.css"
with css_path.open(encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

page = show_sidebar()

if page == "Accueil":
    show_home()
elif page == "Analyser":
    show_property_analysis()
elif page == "Marché":
    show_markets()
elif page == "Premium":
    show_premium()
elif page == "Mes propriétés":
    show_saved_analyses()
elif page == "Mon compte":
    show_account()
elif page == "Administration":
    show_admin()
elif page == "Donner mon avis":
    show_feedback()
elif page == "Confidentialité":
    show_privacy()
else:
    show_about()
