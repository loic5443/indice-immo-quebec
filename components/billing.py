"""Commercial Premium actions; all ownership checks live in the service layer."""
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from components.sidebar import go_to
from services.billing_service import (
    BillingError, billing_account, billing_config, confirm_checkout,
    create_checkout, create_portal, premium_offer, refresh_subscription,
)


@st.cache_data(ttl=300, show_spinner=False)
def _offer():
    return premium_offer()


def available_offer():
    try:
        return _offer(), None
    except BillingError as error:
        return None, str(error)


def _open_account_for_premium():
    """Keep the purchase intent through login and required onboarding."""
    st.session_state["return_to_premium_after_auth"] = True
    st.session_state.pop("return_to_analysis_after_auth", None)
    go_to("Mon compte")


def handle_billing_return(user, database_path):
    """Keep a return across login; an untrusted URL can never set the plan."""
    if "billing" not in st.query_params:
        return
    outcome = st.query_params.get("billing")
    if not user:
        st.session_state["pending_billing_return"] = {"billing": outcome, "session_id": st.query_params.get("session_id", "")}
        st.query_params.pop("billing", None)
        st.query_params.pop("session_id", None)
        st.info("Connectez-vous au compte utilisé pour votre abonnement. Votre paiement sera vérifié ensuite.")
        st.button("Se connecter pour retrouver mon abonnement", on_click=go_to, args=("Mon compte",), key="billing_return_login")
        return
    try:
        if outcome == "success":
            session_id = st.query_params.get("session_id", "")
            if not session_id.startswith("cs_") or len(session_id) > 255:
                raise BillingError("Le retour de paiement est invalide.")
            if confirm_checkout(user["id"], session_id, database_path):
                st.success("Premium est actif. Retrouvez vos dossiers, comparaisons, rapports et suivi dans votre espace.")
            else:
                st.info("Votre paiement n’est pas encore confirmé. Vous pouvez actualiser votre abonnement ci-dessous.")
        elif outcome == "portal":
            refresh_subscription(user["id"], database_path)
            st.info("Votre abonnement a été actualisé.")
        elif outcome == "cancel":
            st.info("Le paiement n’a pas été terminé. Vous pouvez continuer avec le forfait gratuit.")
    except BillingError as error:
        st.error(str(error))
    finally:
        st.query_params.pop("billing", None)
        st.query_params.pop("session_id", None)


def show_billing_actions(user, database_path, offer):
    if offer is None:
        return
    if offer["mode"] == "test":
        st.warning("Mode de test : aucun paiement réel. Utilisez uniquement une carte de test Stripe.")
    if user is None:
        st.button("Créer mon compte pour choisir Premium", type="primary", on_click=_open_account_for_premium,
                  key="billing_signup", width="stretch")
        return
    account = billing_account(user["id"], database_path)
    if account:
        labels = {"active": "Actif", "trialing": "Essai actif", "past_due": "Paiement à régulariser",
                  "canceled": "Terminé", "unpaid": "Paiement non réglé", "incomplete": "Paiement à terminer",
                  "incomplete_expired": "Paiement expiré", "none": "En attente"}
        st.caption("Abonnement : " + labels.get(account["status"], "À vérifier"))
        if account["cancel_at_period_end"] and account["access_until"]:
            date = datetime.fromtimestamp(account["access_until"], ZoneInfo("America/Toronto")).strftime("%Y-%m-%d")
            st.info(f"Renouvellement annulé. Votre accès reste disponible jusqu’au {date} si votre abonnement est actif.")
        if st.button("Gérer mon abonnement et mes factures", key="billing_manage", width="stretch"):
            try:
                st.session_state["billing_portal_url"] = create_portal(user["id"], database_path)
                st.session_state["billing_portal_owner"] = user["id"]
            except BillingError as error:
                st.error(str(error))
        if st.session_state.get("billing_portal_owner") == user["id"] and st.session_state.get("billing_portal_url"):
            st.link_button("Ouvrir mon espace de facturation", st.session_state["billing_portal_url"], width="stretch")
        if st.button("Actualiser mon abonnement", key="billing_refresh", width="stretch"):
            try:
                refresh_subscription(user["id"], database_path)
                st.rerun()
            except BillingError as error:
                st.error(str(error))
    # A canceled subscription may be purchased again. Failed/incomplete ones use
    # the portal, rather than creating an accidental second recurring charge.
    if not account or account["status"] in {"none", "canceled", "incomplete_expired"}:
        if st.button("Choisir Premium", type="primary", key="billing_checkout", width="stretch"):
            try:
                st.session_state["billing_checkout_url"] = create_checkout(user["id"], database_path)
                st.session_state["billing_checkout_owner"] = user["id"]
            except BillingError as error:
                st.error(str(error))
        if st.session_state.get("billing_checkout_owner") == user["id"] and st.session_state.get("billing_checkout_url"):
            st.link_button("Continuer vers le paiement sécurisé", st.session_state["billing_checkout_url"], type="primary", width="stretch")
        st.caption("Abonnement mensuel renouvelé automatiquement. Annulation du renouvellement dans votre espace de facturation. Le total applicable est affiché avant confirmation.")
