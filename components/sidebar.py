"""Compact product navigation with secondary destinations kept out of the main flow."""

import streamlit as st


PRIMARY_PAGES = ["Accueil", "Analyser", "Mes propriétés", "Marché", "Premium"]
SECONDARY_PAGES = ["Mon compte", "À propos", "Confidentialité", "Donner mon avis"]
PAGE_ALIASES = {
    "Analyse immobilière": "Analyser",
    "Mes analyses": "Mes propriétés",
    "Marchés": "Marché",
    "Compte": "Mon compte",
}


def go_to(page: str) -> None:
    """Navigate through one canonical page state while preserving old callers."""

    st.session_state["main_navigation"] = PAGE_ALIASES.get(page, page)


def _secondary(page: str) -> None:
    go_to(page)


def _primary_changed() -> None:
    go_to(st.session_state.get("primary_navigation", "Accueil"))


def show_sidebar() -> str:
    current = PAGE_ALIASES.get(st.session_state.get("main_navigation", "Accueil"), st.session_state.get("main_navigation", "Accueil"))
    if current not in PRIMARY_PAGES + SECONDARY_PAGES + ["Administration"]:
        current = "Accueil"
    st.session_state["main_navigation"] = current

    st.sidebar.markdown(
        "<div class='brand-mark'>IM</div><h2 class='sidebar-brand'>ImmoRadar</h2>"
        "<p class='sidebar-tagline'>Valeur, analyse et suivi immobilier.</p>",
        unsafe_allow_html=True,
    )
    if current in PRIMARY_PAGES:
        st.session_state["primary_navigation"] = current
    st.session_state.setdefault("primary_navigation", "Accueil")
    st.sidebar.radio(
        "Navigation principale", PRIMARY_PAGES,
        key="primary_navigation", on_change=_primary_changed,
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.caption("Espace personnel")
    account_label = "Mon compte" if "current_user" in st.session_state else "Se connecter"
    if st.sidebar.button(account_label, key="secondary_account", use_container_width=True):
        _secondary("Mon compte")
    with st.sidebar.expander("Informations et aide"):
        if st.button("À propos", key="secondary_about", use_container_width=True):
            _secondary("À propos")
        if st.button("Confidentialité", key="secondary_privacy", use_container_width=True):
            _secondary("Confidentialité")
        if st.button("Donner mon avis", key="secondary_feedback", use_container_width=True):
            _secondary("Donner mon avis")
    if st.session_state.get("current_user", {}).get("role") == "admin":
        if st.sidebar.button("Administration", key="secondary_admin", use_container_width=True):
            _secondary("Administration")
    st.sidebar.caption("Bêta privée · Aucun paiement réel n’est activé.")
    return st.session_state.get("main_navigation", "Accueil")
