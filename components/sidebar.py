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
    # A secondary page must not leave the previous primary destination selected:
    # clicking that already-selected radio would otherwise have no effect.
    st.session_state["primary_navigation"] = current if current in PRIMARY_PAGES else None
    st.sidebar.radio(
        "Navigation principale", PRIMARY_PAGES,
        index=None, key="primary_navigation", on_change=_primary_changed,
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    account_label = "Mon compte" if "current_user" in st.session_state else "Se connecter"
    account_hint = (
        "Vos dossiers, préférences et alertes."
        if "current_user" in st.session_state
        else "Connectez-vous pour sauvegarder vos dossiers."
    )
    st.sidebar.markdown(
        f"<div class='sidebar-account-card'><p>ESPACE PERSONNEL</p><strong>{account_label}</strong>"
        f"<span>{account_hint}</span></div>",
        unsafe_allow_html=True,
    )
    st.sidebar.button(
        f"👤 {account_label} et alertes", key="secondary_account", width="stretch",
        on_click=_secondary, args=("Mon compte",),
    )
    with st.sidebar.expander("Informations et aide"):
        st.button("À propos", key="secondary_about", width="stretch", on_click=_secondary, args=("À propos",))
        st.button("Confidentialité", key="secondary_privacy", width="stretch", on_click=_secondary, args=("Confidentialité",))
        st.button("Donner mon avis", key="secondary_feedback", width="stretch", on_click=_secondary, args=("Donner mon avis",))
    if st.session_state.get("current_user", {}).get("role") == "admin":
        st.sidebar.button("Administration", key="secondary_admin", width="stretch", on_click=_secondary, args=("Administration",))
    st.sidebar.caption("Bêta privée · Aucun paiement réel n’est activé.")
    return st.session_state.get("main_navigation", "Accueil")
