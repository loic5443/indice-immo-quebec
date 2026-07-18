"""ImmoRadar entry point: page composition only."""

from pathlib import Path

import streamlit as st

from components.about import show_about
from components.account import show_account
from components.alerts import show_alert_signup
from components.home import show_home
from components.markets import show_markets
from components.premium import show_premium
from components.property_analysis import show_property_analysis
from components.saved_analyses import show_saved_analyses
from components.sidebar import show_sidebar
from data.database import initialize_database


st.set_page_config(page_title="ImmoRadar", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

initialize_database()

css_path = Path(__file__).resolve().parent / "styles" / "main.css"
with css_path.open(encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

page = show_sidebar()

if page == "Accueil":
    show_home()
    show_alert_signup()
elif page == "Analyse immobilière":
    show_property_analysis()
elif page == "Marchés":
    show_markets()
elif page == "Premium":
    show_premium()
elif page == "Mes analyses":
    show_saved_analyses()
elif page == "Mon compte":
    show_account()
else:
    show_about()
