"""Account screen for the local ImmoRadar MVP."""

import streamlit as st

from components.sidebar import go_to
from data.database import authenticate_user, count_analyses, create_user, validate_registration


def is_authenticated() -> bool:
    return "current_user" in st.session_state


def current_user() -> dict:
    return st.session_state["current_user"]


def logout() -> None:
    st.session_state.pop("current_user", None)
    go_to("Accueil")


def show_account() -> None:
    """Show account credentials forms or the signed-in account summary."""
    st.markdown("<p class='eyebrow'>ESPACE PERSONNEL</p><h1>Mon compte</h1>", unsafe_allow_html=True)
    if is_authenticated():
        user = current_user()
        st.markdown(
            f"<div class='account-summary'><span class='data-pill real'>Connecté</span>"
            f"<h2>{user['name']}</h2><p>{user['email']}</p><p>Forfait : <b>{'Premium' if user['plan'] == 'premium' else 'Gratuit'}</b></p></div>",
            unsafe_allow_html=True,
        )
        analyses, plan = st.columns(2)
        analyses.metric("Analyses sauvegardées", count_analyses(user["id"]))
        plan.metric("Statut du forfait", "Premium" if user["plan"] == "premium" else "Gratuit")
        view, sign_out, _ = st.columns([1, 1, 2])
        view.button("Voir mes analyses", type="primary", on_click=go_to, args=("Mes analyses",), use_container_width=True)
        sign_out.button("Se déconnecter", on_click=logout, use_container_width=True)
        st.caption("Le statut Premium est prévu techniquement; aucun paiement réel n'est activé.")
        return

    st.write("Créez un compte local pour sauvegarder vos analyses, ou connectez-vous à un compte existant.")
    login_tab, register_tab = st.tabs(["Connexion", "Créer un compte"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Adresse courriel", key="login_email")
            password = st.text_input("Mot de passe", type="password", key="login_password")
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
        if submitted:
            user = authenticate_user(email, password)
            if user is None:
                st.error("Adresse courriel ou mot de passe incorrect.")
            else:
                st.session_state["current_user"] = user
                st.success("Connexion réussie.")
                st.rerun()
    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Nom")
            email = st.text_input("Adresse courriel", key="register_email")
            password = st.text_input("Mot de passe", type="password", key="register_password")
            confirmation = st.text_input("Confirmer le mot de passe", type="password")
            submitted = st.form_submit_button("Créer mon compte", type="primary", use_container_width=True)
        if submitted:
            errors = validate_registration(name, email, password, confirmation)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                created, message = create_user(name, email, password)
                if created:
                    st.success(message)
                else:
                    st.error(message)
