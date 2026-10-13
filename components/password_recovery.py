"""Self-service recovery UI; never displays or logs the recovery token."""
import streamlit as st

from services.password_recovery_service import recovery_ready, request_recovery, redeem_recovery


def show_recovery(database_path):
    token = st.query_params.get("reset_token")
    if token:
        st.subheader("Choisir un nouveau mot de passe")
        with st.form("password_recovery_redeem"):
            password = st.text_input("Nouveau mot de passe", type="password", key="recovery_new_password")
            confirmation = st.text_input("Confirmer le nouveau mot de passe", type="password", key="recovery_confirmation")
            submitted = st.form_submit_button("Enregistrer mon nouveau mot de passe", type="primary")
        if submitted:
            ok, message = redeem_recovery(token, password, confirmation, database_path)
            if ok:
                st.session_state.clear()
                st.query_params.pop("reset_token", None)
                st.success(message)
            else:
                st.error(message)
        if st.button("Revenir à la connexion", key="recovery_back"):
            st.query_params.pop("reset_token", None)
            st.rerun()
        return True
    with st.expander("Mot de passe oublié ?"):
        if not recovery_ready():
            st.info("La récupération par courriel est en préparation. Aucun lien ne peut encore être envoyé depuis ce site.")
            return False
        with st.form("password_recovery_request"):
            email = st.text_input("Courriel de votre compte", key="recovery_email")
            submitted = st.form_submit_button("Recevoir un lien de récupération")
        if submitted:
            if not email.strip():
                st.error("Le courriel est requis.")
            else:
                ok, message = request_recovery(email, database_path)
                (st.success if ok else st.info)(message)
    return False
