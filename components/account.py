"""Account screen for the local ImmoRadar MVP."""

import streamlit as st

from components.sidebar import go_to
from data.database import authenticate_user, count_analyses, create_user, get_user, validate_registration
from data.database import DATABASE_PATH
from domain.models import UserProfile
from services.privacy_service import delete_account, export_user_data


def is_authenticated() -> bool:
    return _active_user() is not None


def current_user() -> dict:
    user = _active_user()
    if user is None:
        raise RuntimeError("Aucune session utilisateur active.")
    return user


def initialize_session() -> None:
    """Validate a persisted Streamlit session against the local account record."""
    _active_user()


def _active_user() -> dict | None:
    session_user = st.session_state.get("current_user")
    if not isinstance(session_user, dict) or not isinstance(session_user.get("id"), int):
        st.session_state.pop("current_user", None)
        return None
    user = get_user(session_user["id"])
    if user is None:
        st.session_state.pop("current_user", None)
        return None
    # Refresh non-sensitive account data such as plan or profile at each request.
    st.session_state["current_user"] = user
    return user


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
            f"<h2>{user['name']}</h2><p>{user['email']}</p><p>Forfait : <b>{'Premium' if user['plan'] == 'premium' else 'Gratuit'}</b></p>"
            f"<p>Profil : <b>{user['user_type']}</b> · {user['investment_horizon']} · risque {user['risk_tolerance']}</p></div>",
            unsafe_allow_html=True,
        )
        analyses, plan = st.columns(2)
        analyses.metric("Analyses sauvegardées", count_analyses(user["id"]))
        plan.metric("Statut du forfait", "Premium" if user["plan"] == "premium" else "Gratuit")
        view, sign_out, _ = st.columns([1, 1, 2])
        view.button("Voir mes analyses", type="primary", on_click=go_to, args=("Mes analyses",), use_container_width=True)
        sign_out.button("Se déconnecter", on_click=logout, use_container_width=True)
        st.divider()
        st.subheader("Vie privée et contrôle")
        st.download_button("Télécharger mes données", export_user_data(user["id"], DATABASE_PATH), "immoradar-mes-donnees.json", "application/json")
        st.caption("L'export contient votre profil et vos analyses, jamais votre mot de passe. La suppression efface définitivement le compte, ses analyses et ses retours.")
        confirmation = st.text_input("Pour supprimer, tapez SUPPRIMER", key="delete_account_confirmation")
        if st.button("Supprimer définitivement mon compte", type="secondary"):
            if confirmation != "SUPPRIMER": st.error("Confirmation requise : tapez SUPPRIMER.")
            elif delete_account(user["id"], DATABASE_PATH):
                logout(); st.success("Compte supprimé."); st.rerun()
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
            user_type = st.selectbox("Type d'utilisateur", ["Premier acheteur", "Investisseur locatif", "Propriétaire", "Courtier ou analyste"])
            investment_horizon = st.selectbox("Horizon d'investissement", ["Moins de 2 ans", "2 à 5 ans", "Plus de 5 ans"])
            risk_tolerance = st.selectbox("Tolérance au risque", ["Prudent", "Modéré", "Élevé"], index=1)
            submitted = st.form_submit_button("Créer mon compte", type="primary", use_container_width=True)
        if submitted:
            profile = UserProfile(user_type, investment_horizon, risk_tolerance)
            errors = validate_registration(name, email, password, confirmation, profile)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                created, message = create_user(name, email, password, profile=profile)
                if created:
                    st.success(message)
                else:
                    st.error(message)
