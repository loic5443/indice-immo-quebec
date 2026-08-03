"""Account screen for the local ImmoRadar MVP."""

import streamlit as st

from components.sidebar import go_to
from data.database import authenticate_user, count_analyses, create_user, get_user, validate_registration
from data.database import DATABASE_PATH
from domain.models import UserProfile
from services.privacy_service import delete_account, export_user_data
from services.onboarding_service import STEPS, complete, progress
from services.beta_service import registration_allowed, consume_invitation
from repositories.sqlite_repository import SQLiteRepository
from services.entitlements_service import quota_status
from services.auth_service import validate_login_submission


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
    st.markdown("<p class='eyebrow'>ESPACE PERSONNEL</p>", unsafe_allow_html=True)
    st.title("Mon compte")
    if is_authenticated():
        user = current_user()
        if not user.get("onboarding_completed"):
            _show_onboarding(user)
            return
        st.markdown(
            f"<div class='account-summary'><span class='data-pill real'>Connecté</span>"
            f"<h2>{user['name']}</h2><p>{user['email']}</p><p>Forfait : <b>{'Premium' if user['plan'] == 'premium' else 'Gratuit'}</b></p>"
            f"<p>Profil : <b>{user['user_type']}</b> · {user['investment_horizon']} · risque {user['risk_tolerance']}</p></div>",
            unsafe_allow_html=True,
        )
        analyses, plan = st.columns(2)
        analyses.metric("Analyses sauvegardées", count_analyses(user["id"]))
        plan.metric("Statut du forfait", "Premium" if user["plan"] == "premium" else "Gratuit")
        st.caption(quota_status(user["id"], user, DATABASE_PATH)["label"])
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
            errors = validate_login_submission(email, password)
            if errors:
                for error in errors:
                    st.error(error)
            elif (user := authenticate_user(email, password)) is None:
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
            invitation_code = st.text_input("Code d'invitation bêta (si requis)")
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
                allowed, beta_message = registration_allowed(invitation_code, DATABASE_PATH)
                if not allowed:
                    st.error(beta_message)
                    return
                created, message = create_user(name, email, password, profile=profile)
                if created:
                    if invitation_code and not consume_invitation(invitation_code, DATABASE_PATH):
                        st.error("Compte créé, mais le code n'a pas pu être consommé. Contactez l'administrateur.")
                    else: st.success(message)
                else:
                    st.error(message)


def _show_onboarding(user: dict) -> None:
    step = int(user.get("onboarding_step") or 1)
    st.markdown("<p class='eyebrow'>DÉMARRAGE</p><h1>Bienvenue dans ImmoRadar</h1>", unsafe_allow_html=True)
    st.progress(step / len(STEPS), text=f"Étape {step} sur {len(STEPS)} — {STEPS[step-1]}")
    if step == 1: st.write("Analysez vos hypothèses avec plus de clarté, avant d'en discuter avec un professionnel.")
    elif step == 2: progress(user["id"], DATABASE_PATH, user_type=st.selectbox("Votre profil", ["Premier acheteur", "Investisseur locatif", "Propriétaire", "Courtier ou analyste"], index=1 if user["user_type"] == "Investisseur locatif" else 0))
    elif step == 3: progress(user["id"], DATABASE_PATH, user_objective=st.text_input("Votre objectif principal", value=user.get("user_objective") or ""))
    elif step == 4: progress(user["id"], DATABASE_PATH, investment_horizon=st.selectbox("Horizon (facultatif)", ["", "Moins de 2 ans", "2 à 5 ans", "5 à 10 ans", "Plus de 10 ans"], index=0))
    elif step == 5: progress(user["id"], DATABASE_PATH, risk_tolerance=st.selectbox("Tolérance au risque (facultatif)", ["", "Prudente", "Équilibrée", "Élevée"], index=0))
    elif step == 6: st.info("ImmoValue propose une fourchette expérimentale à partir des comparables que vous fournissez.")
    elif step == 7: st.info("ImmoScore mesure l'adéquation de vos hypothèses financières à votre profil.")
    elif step == 8: st.info("La confiance mesure la qualité et la complétude des données, pas la probabilité d'un bon achat.")
    else:
        accepted=st.checkbox("Je reconnais qu'ImmoRadar n'est pas une évaluation officielle, ne remplace pas un professionnel et ne garantit aucune recommandation.")
        if accepted: progress(user["id"], DATABASE_PATH, limitations_accepted=1)
    left,right=st.columns(2)
    if left.button("Précédent", disabled=step==1): progress(user["id"], DATABASE_PATH, onboarding_step=step-1); st.rerun()
    if step < len(STEPS):
        if right.button("Suivant"):
            if step==2 and not SQLiteRepository(DATABASE_PATH).get_user_by_id(user["id"])["user_type"]: st.error("Profil requis.")
            elif step==3 and not SQLiteRepository(DATABASE_PATH).get_user_by_id(user["id"])["user_objective"]: st.error("Objectif requis.")
            else: progress(user["id"], DATABASE_PATH, onboarding_step=step+1); st.rerun()
    elif right.button("Terminer"):
        if complete(user["id"], DATABASE_PATH): st.success("Onboarding terminé."); st.rerun()
        else: st.error("Profil, objectif et reconnaissance des limites requis.")
