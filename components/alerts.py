"""Alert centre: factual alerts only, with clearly locked Premium previews."""

import streamlit as st

from components.sidebar import go_to
from services.entitlements_service import can_use


def show_alert_center(user: dict, analyses: list[dict]) -> None:
    st.markdown("<div class='section-space compact-space'></div><h2>Centre d’alertes</h2>", unsafe_allow_html=True)
    if not can_use(user, "alerts"):
        st.markdown("<section class='premium-notice'><p class='eyebrow'>APERÇU PREMIUM VERROUILLÉ</p><h3>Surveillez ce qui peut changer votre décision</h3><p>Alertes de variation de valeur, impact de taux, mise à jour du rôle municipal et détérioration de marge financière. Elles ne sont pas actives pour ce forfait.</p></section>", unsafe_allow_html=True)
        st.button("Découvrir Premium", on_click=go_to, args=("Premium",), key="alerts_premium")
        return
    # No message is produced unless a comparison or a source update is truly
    # available. This avoids turning examples into apparent real events.
    st.info("Aucune alerte calculable pour le moment. Le suivi s’activera seulement lorsqu’un changement vérifiable est disponible dans vos dossiers ou vos sources autorisées.")
    st.caption("Aucun courriel n’est envoyé pendant la bêta privée.")
