"""Account screen for the local ImmoRadar MVP."""

from html import escape

import streamlit as st

from components.sidebar import go_to
from components.premium_teaser import show_premium_teaser
from data.database import authenticate_user, count_analyses, create_user, get_user, validate_registration
from data.database import DATABASE_PATH
from services.privacy_service import delete_account, export_user_data
from services.onboarding_service import STEPS, complete, progress
from services.beta_service import registration_allowed, consume_invitation
from services.entitlements_service import can_use, quota_is_enforced, quota_status
from services.auth_service import validate_login_submission


RETURN_TO_ANALYSIS_KEY = "return_to_analysis_after_auth"


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


def _resume_analysis_after_authentication() -> bool:
    """Return to the in-session draft only after a valid account journey.

    The destination is deliberately fixed instead of accepting arbitrary page
    names: a registration flow must never become an open redirect.
    """

    if not st.session_state.pop(RETURN_TO_ANALYSIS_KEY, False):
        return False
    go_to("Analyser")
    return True


def _start_new_account_session(email: str, password: str) -> dict | None:
    """Authenticate a new local account and defer preferences to onboarding."""

    user = authenticate_user(email, password)
    if user is None:
        return None
    # New accounts select their actual profile in onboarding. Existing users
    # are never passed through this path, so their saved choices stay intact.
    progress(user["id"], DATABASE_PATH, user_type="", investment_horizon="", risk_tolerance="", onboarding_step=1)
    user = authenticate_user(email, password)
    if user is not None:
        st.session_state["current_user"] = user
    return user


def show_account() -> None:
    """Show account credentials forms or the signed-in account summary."""
    st.markdown("<p class='eyebrow'>ESPACE PERSONNEL</p>", unsafe_allow_html=True)
    st.title("Mon compte")
    if is_authenticated():
        user = current_user()
        if not user.get("onboarding_completed"):
            _show_onboarding(user)
            return
        if _resume_analysis_after_authentication():
            st.rerun()
        safe_name = escape(str(user.get("name") or ""))
        safe_email = escape(str(user.get("email") or ""))
        safe_profile = escape(str(user.get("user_type") or ""))
        safe_horizon = escape(str(user.get("investment_horizon") or ""))
        safe_risk = escape(str(user.get("risk_tolerance") or ""))
        st.markdown(
            f"<div class='account-summary'><span class='data-pill real'>Connecté</span>"
            f"<h2>{safe_name}</h2><p>{safe_email}</p><p>Forfait : <b>{'Premium' if user['plan'] == 'premium' else 'Gratuit'}</b></p>"
            f"<p>Profil : <b>{safe_profile}</b> · {safe_horizon} · risque {safe_risk}</p></div>",
            unsafe_allow_html=True,
        )
        analysis_count = count_analyses(user["id"])
        analyses, plan = st.columns(2)
        analyses.metric("Analyses sauvegardées", analysis_count)
        plan.metric("Statut du forfait", "Premium" if user["plan"] == "premium" else "Gratuit")
        quota = quota_status(user["id"], user, DATABASE_PATH)
        if quota_is_enforced(DATABASE_PATH):
            st.caption(quota["label"])
        else:
            st.caption("Quota mensuel en aperçu pendant la bêta : aucune estimation n’est déduite automatiquement.")
        primary, sign_out, _ = st.columns([1, 1, 2])
        if analysis_count:
            primary.button("Voir mes propriétés", type="primary", on_click=go_to, args=("Mes propriétés",), use_container_width=True)
        else:
            st.info("Votre espace est prêt. Commencez par analyser une propriété : vous pourrez ensuite conserver votre dossier et vos scénarios ici.")
            primary.button("Analyser une propriété", type="primary", on_click=go_to, args=("Analyser",), use_container_width=True)
        sign_out.button("Se déconnecter", on_click=logout, use_container_width=True)
        if not can_use(user, "advanced_comparisons"):
            show_premium_teaser(
                feature="Dossiers suivis, comparaisons, scénarios et rapports",
                title="Passez du calcul ponctuel au suivi de vos décisions.",
                detail="Premium réunit les instantanés, les comparaisons détaillées, le rapport PDF et les changements vérifiables de vos dossiers sauvegardés.",
                key="account_premium",
            )
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
            st.caption("Vous choisirez votre profil et vos préférences dans le court démarrage suivant."
                       " Ces choix peuvent être modifiés plus tard dans Mon compte.")
            submitted = st.form_submit_button("Créer mon compte", type="primary", use_container_width=True)
        if submitted:
            errors = validate_registration(name, email, password, confirmation)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                allowed, beta_message = registration_allowed(invitation_code, DATABASE_PATH)
                if not allowed:
                    st.error(beta_message)
                    return
                created, message = create_user(name, email, password)
                if created:
                    if invitation_code and not consume_invitation(invitation_code, DATABASE_PATH):
                        st.error("Compte créé, mais le code n'a pas pu être consommé. Contactez l'administrateur.")
                    else:
                        # The user has just proven control of the chosen password.
                        # Start the local session directly; the mandatory onboarding
                        # is still shown before any personal area is available.
                        user = _start_new_account_session(email, password)
                        if user is None:
                            st.error("Compte créé, mais la connexion locale n’a pas pu démarrer. Connectez-vous avec vos identifiants.")
                        else:
                            st.session_state["account_creation_notice"] = message
                            st.rerun()
                else:
                    st.error(message)


def _show_onboarding(user: dict) -> None:
    """Render a resumable onboarding without mutating a profile on display."""

    step = int(user.get("onboarding_step") or 1)
    st.markdown("<p class='eyebrow'>DÉMARRAGE</p><h1>Bienvenue dans ImmoRadar</h1>", unsafe_allow_html=True)
    creation_notice = st.session_state.pop("account_creation_notice", None)
    if isinstance(creation_notice, str) and creation_notice:
        st.success(creation_notice)
    st.progress(step / len(STEPS), text=f"Étape {step} sur {len(STEPS)} — {STEPS[step-1]}")
    profile_options = ["", "Premier acheteur", "Investisseur locatif", "Propriétaire", "Courtier ou analyste"]
    horizon_options = ["", "Moins de 2 ans", "2 à 5 ans", "5 à 10 ans", "Plus de 10 ans"]
    risk_options = ["", "Prudent", "Modéré", "Élevé"]
    selected_profile = user.get("user_type") if user.get("user_type") in profile_options else ""
    selected_horizon = user.get("investment_horizon") if user.get("investment_horizon") in horizon_options else ""
    selected_risk = user.get("risk_tolerance") if user.get("risk_tolerance") in risk_options else ""
    if step == 1:
        st.write("Analysez vos hypothèses avec plus de clarté, avant d’en discuter avec un professionnel.")
    elif step == 2:
        selected_profile = st.selectbox(
            "Votre profil", profile_options,
            index=profile_options.index(selected_profile) if selected_profile else 0,
            format_func=lambda value: value or "Choisissez votre profil",
        )
    elif step == 3:
        objective = st.text_input("Votre objectif principal", value=user.get("user_objective") or "")
    elif step == 4:
        selected_horizon = st.selectbox("Horizon (facultatif)", horizon_options, index=horizon_options.index(selected_horizon))
    elif step == 5:
        selected_risk = st.selectbox("Tolérance au risque (facultatif)", risk_options, index=risk_options.index(selected_risk))
    elif step == 6:
        st.info("ImmoValue propose une fourchette expérimentale à partir des comparables que vous fournissez.")
    elif step == 7:
        st.info("ImmoScore mesure l’adéquation de vos hypothèses financières à votre profil.")
    elif step == 8:
        st.info("La confiance mesure la qualité et la complétude des données, pas la probabilité d’un bon achat.")
    else:
        accepted = st.checkbox("Je reconnais qu’ImmoRadar n’est pas une évaluation officielle, ne remplace pas un professionnel et ne garantit aucune recommandation.", value=bool(user.get("limitations_accepted")))
    left, later, right = st.columns(3)
    if left.button("Précédent", disabled=step == 1):
        progress(user["id"], DATABASE_PATH, onboarding_step=step - 1)
        st.rerun()
    if later.button("Reprendre plus tard"):
        go_to("Accueil")
        st.rerun()
    if step < len(STEPS):
        if right.button("Suivant"):
            values = {"onboarding_step": step + 1}
            if step == 2:
                values["user_type"] = selected_profile
                if not selected_profile:
                    st.error("Choisissez votre profil pour continuer.")
                    return
            elif step == 3:
                values["user_objective"] = objective.strip()
                if not values["user_objective"]:
                    st.error("Indiquez votre objectif principal pour continuer.")
                    return
            elif step == 4:
                values["investment_horizon"] = selected_horizon
            elif step == 5:
                values["risk_tolerance"] = selected_risk
            progress(user["id"], DATABASE_PATH, **values)
            st.rerun()
    elif right.button("Terminer"):
        progress(user["id"], DATABASE_PATH, limitations_accepted=1 if accepted else 0)
        if complete(user["id"], DATABASE_PATH):
            st.success("Onboarding terminé.")
            _resume_analysis_after_authentication()
            st.rerun()
        else: st.error("Profil, objectif et reconnaissance des limites requis.")
