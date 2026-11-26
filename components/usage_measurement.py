"""Optional measurement remains off until the visitor chooses it."""
import sqlite3
import uuid
import streamlit as st
from data.database import DATABASE_PATH
from services.usage_measurement import record

def measure(event):
    if not st.session_state.get("usage_consent", False):
        return
    session=st.session_state.setdefault("usage_session", uuid.uuid4().hex)
    try:
        record(DATABASE_PATH, session, event, consent=True)
    except sqlite3.Error:
        pass  # Measuring must never block an analysis or payment.

def show_measurement_choice():
    with st.expander("Confidentialité et statistiques facultatives"):
        st.checkbox("Aider à améliorer Cenlio avec des statistiques de cette visite (facultatif)", key="usage_consent", value=False)
        st.caption("Désactivé par défaut. Aucune adresse, aucun montant ni courriel dans ces statistiques. Identifiant aléatoire limité à cette session, conservation de 90 jours. Vous pouvez retirer votre accord ici.")
    measure("visit")
