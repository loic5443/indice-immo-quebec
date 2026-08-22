"""Alert centre: factual alerts only, with clearly locked Premium previews."""

import streamlit as st

from components.sidebar import go_to
from components.premium_teaser import show_premium_teaser
from data.database import DATABASE_PATH
from services.alert_service import build_calculable_alerts
from services.analysis_reopen_service import AnalysisReopenAccessError, prepare_reopen_draft
from services.entitlements_service import can_use


def show_alert_center(user: dict, analyses: list[dict], *, tracking_configured: bool = False) -> None:
    st.markdown("<div class='section-space compact-space'></div><h2>Centre d’alertes</h2>", unsafe_allow_html=True)
    if not can_use(user, "alerts"):
        show_premium_teaser(
            feature="Suivi des changements vérifiables",
            title="Revenez au bon dossier au bon moment.",
            detail="Premium ajoute le suivi local des variations de rôle municipal, d’ImmoValue, de sensibilité au taux et du renouvellement que vous avez saisi.",
            key="alerts_premium",
        )
        return
    if tracking_configured and not analyses:
        st.info("Aucun dossier suivi pour le moment. Activez le suivi d’un dossier dans Mes propriétés pour voir uniquement les changements vérifiables qui le concernent.")
        st.markdown(
            "<div class='data-card'><div><span class='data-pill simulated'>PROCHAINE ÉTAPE</span>"
            "<h3>Choisissez un dossier à suivre</h3><p>Le suivi compare uniquement ses instantanés sauvegardés. "
            "Aucune donnée n’est devinée et aucune alerte n’est créée avant qu’un changement puisse être établi.</p>"
            "</div></div>",
            unsafe_allow_html=True,
        )
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
    st.success("Vos dossiers suivis ne signalent aucun changement vérifiable pour le moment.")
    st.markdown(
        "<div class='data-card'><div><span class='data-pill real'>SUIVI LOCAL ACTIF</span>"
        "<h3>Ce qu’ImmoRadar peut vous signaler</h3><p>Une variation entre deux valeurs municipales ou deux ImmoValue fiables, "
        "une sensibilité au taux devenue négative, ou un rappel de renouvellement que vous avez vous-même saisi.</p>"
        "</div><div><span class='data-pill simulated'>PAS UNE PRÉVISION</span>"
        "<h3>Ce qui reste indisponible</h3><p>Sans nouvel instantané, source autorisée ou date fournie, aucun changement n’est affiché. "
        "ImmoRadar ne crée pas de notification à partir d’une supposition.</p></div></div>",
        unsafe_allow_html=True,
    )
    st.caption("Aucun courriel n’est envoyé pendant la bêta privée.")
