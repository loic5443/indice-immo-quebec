"""Primary product navigation."""

import streamlit as st


PAGES = ["Accueil", "Analyse immobilière", "Marchés", "Premium", "Mes analyses", "Mon compte", "À propos"]


def go_to(page: str) -> None:
    st.session_state["main_navigation"] = page


def show_sidebar() -> str:
    st.sidebar.markdown("<div class='brand-mark'>IM</div><h2 class='sidebar-brand'>ImmoRadar</h2><p class='sidebar-tagline'>L'immobilier, avec plus de clarté.</p>", unsafe_allow_html=True)
    pages=list(PAGES) + ["Donner mon avis"]
    if st.session_state.get("current_user",{}).get("role")=="admin": pages.append("Administration")
    page = st.sidebar.radio("Navigation principale", pages, key="main_navigation", label_visibility="collapsed")
    st.sidebar.divider()
    if "current_user" in st.session_state:
        st.sidebar.caption(f"Connecté : {st.session_state['current_user']['email']}")
    else:
        st.sidebar.caption("Connectez-vous pour sauvegarder vos analyses. Aucun paiement réel n'est activé.")
    return page
