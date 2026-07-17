"""Primary product navigation."""

import streamlit as st


PAGES = ["Accueil", "Analyse immobilière", "Marchés", "Premium", "À propos"]


def go_to(page: str) -> None:
    st.session_state["main_navigation"] = page


def show_sidebar() -> str:
    st.sidebar.markdown("<div class='brand-mark'>IM</div><h2 class='sidebar-brand'>ImmoRadar</h2><p class='sidebar-tagline'>L'immobilier, avec plus de clarté.</p>", unsafe_allow_html=True)
    page = st.sidebar.radio("Navigation principale", PAGES, key="main_navigation", label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Aucun paiement, abonnement réel ou compte utilisateur n'est activé.")
    return page
