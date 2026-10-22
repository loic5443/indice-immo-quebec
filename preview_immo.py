"""Temporary preview entry point. Never use this service for production data."""
import os
import runpy
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st

# The preview cannot send email or initiate payments, even if secrets are set.
for key in (
    "IMMORADAR_BILLING_ENABLED", "IMMORADAR_AUTH_EMAIL_ENABLED",
    "IMMORADAR_OPERATIONS_ENABLED", "IMMORADAR_BACKUPS_ENABLED",
):
    os.environ[key] = "0"
os.environ["IMMORADAR_ALERT_DELIVERY_ENABLED"] = "false"

st.set_page_config(page_title="Cenlio — aperçu temporaire", page_icon="🏠", layout="wide")
st.warning(
    "APERÇU TEMPORAIRE GRATUIT — Paiements et courriels désactivés. "
    "Les comptes et dossiers peuvent disparaître au redémarrage. "
    "Utilisez uniquement des données fictives et un mot de passe réservé aux essais."
)
# This preview-only route checks the actual hosted page at phone widths.
qa_width = st.query_params.get("qa_width")
origin = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
parsed_origin = urlsplit(origin)
if (qa_width in {"360", "390", "430", "768"} and parsed_origin.scheme == "https"
        and parsed_origin.hostname and not parsed_origin.username and not parsed_origin.password
        and parsed_origin.path in {"", "/"} and not parsed_origin.query and not parsed_origin.fragment):
    st.caption(f"Contrôle du rendu à {qa_width} px dans le navigateur courant; ce n’est pas une émulation de Safari ou d’Android.")
    st.iframe(origin + "/?embed=true", width=int(qa_width), height=900, alt="Cenlio à largeur mobile")
    st.stop()
runpy.run_path(str(Path(__file__).with_name("indice_immo.py")), run_name="__main__")
