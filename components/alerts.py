"""Alert centre: factual alerts only, with clearly locked Premium previews."""

import streamlit as st

from components.sidebar import go_to
from data.database import DATABASE_PATH
from services.alert_service import build_calculable_alerts
from services.analysis_reopen_service import AnalysisReopenAccessError, prepare_reopen_draft
from services.entitlements_service import can_use


def show_alert_center(user: dict, analyses: list[dict], *, tracking_configured: bool = False) -> None:
    st.markdown("<div class='section-space compact-space'></div><h2>Centre d’alertes</h2>", unsafe_allow_html=True)
    if not can_use(user, "alerts"):
        st.markdown("<section class='premium-notice'><p class='eyebrow'>APERÇU PREMIUM VERROUILLÉ</p><h3>Surveillez ce qui peut changer votre décision</h3><p>Alertes de variation de valeur, impact de taux, mise à jour du rôle municipal et détérioration de marge financière. Elles ne sont pas actives pour ce forfait.</p></section>", unsafe_allow_html=True)
        st.button("Découvrir Premium", on_click=go_to, args=("Premium",), key="alerts_premium")
        return
    if tracking_configured and not analyses:
        st.info("Aucun dossier suivi pour le moment. Activez le suivi d’un dossier dans Mes propriétés pour voir uniquement les changements vérifiables qui le concernent.")
        st.caption("Aucun courriel n’est envoyé pendant la bêta privée.")
        return
    alerts = build_calculable_alerts(analyses)
    if alerts:
        st.caption("Alertes calculées à partir de vos instantanés sauvegardés. Aucun courriel n’est envoyé pendant la bêta privée.")
        for alert in alerts:
            with st.container(border=True):
                label = "À VÉRIFIER" if alert["severity"] == "important" else "MISE À JOUR DISPONIBLE"
                st.markdown(f"<p class='eyebrow'>{label}</p>", unsafe_allow_html=True)
                st.subheader(alert["title"])
                st.write(alert["detail"])
                st.caption(f"Dossier : {alert['property_name']} · instantané du {str(alert['created_at'])[:10]}")
                user_id = user.get("id")
                if isinstance(user_id, int):
                    if st.button("Ouvrir et modifier ce dossier", key=f"alert_open_{alert['analysis_id']}"):
                        try:
                            st.session_state["analysis_reopen_pending"] = prepare_reopen_draft(
                                user_id, int(alert["analysis_id"]), DATABASE_PATH,
                            )
                        except AnalysisReopenAccessError:
                            st.error("Ce dossier n’est pas disponible dans votre espace.")
                        else:
                            go_to("Analyser")
                            st.rerun()
        return
    # No message is produced unless a comparison or a source update is truly
    # available. This avoids turning examples into apparent real events.
    st.info("Aucune alerte calculable pour le moment. Le suivi s’activera seulement lorsqu’un changement vérifiable est disponible dans vos dossiers ou vos sources autorisées.")
    st.caption("Aucun courriel n’est envoyé pendant la bêta privée.")
