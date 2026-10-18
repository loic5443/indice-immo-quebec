"""Temporary preview entry point. Never use this service for production data."""
import os
import runpy
from pathlib import Path

import streamlit as st

# The preview cannot send email or initiate payments, even if secrets are set.
for key in (
    "IMMORADAR_BILLING_ENABLED", "IMMORADAR_AUTH_EMAIL_ENABLED",
    "IMMORADAR_OPERATIONS_ENABLED", "IMMORADAR_BACKUPS_ENABLED",
):
    os.environ[key] = "0"
os.environ["IMMORADAR_ALERT_DELIVERY_ENABLED"] = "false"

st.set_page_config(page_title="ImmoRadar — aperçu temporaire", page_icon="🏠", layout="wide")
st.warning(
    "APERÇU TEMPORAIRE GRATUIT — Paiements et courriels désactivés. "
    "Les comptes et dossiers peuvent disparaître au redémarrage. "
    "Utilisez uniquement des données fictives et un mot de passe réservé aux essais."
)
runpy.run_path(str(Path(__file__).with_name("indice_immo.py")), run_name="__main__")
