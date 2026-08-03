"""Saved-analysis history, always scoped to the signed-in user."""

import json
import streamlit as st

from components.account import current_user, is_authenticated
from components.sidebar import go_to
from components.alerts import show_alert_center
from data.database import delete_analysis, list_analyses, toggle_favorite
from services.report_service import generate_report_pdf


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def show_saved_analyses() -> None:
    """Show the active user's saved analyses and management actions."""
    st.markdown("<p class='eyebrow'>VOS DOSSIERS</p>", unsafe_allow_html=True)
    st.title("Mes propriétés")
    st.markdown("<p class='section-intro'>Retrouvez vos dossiers sauvegardés, leurs points de repère et le suivi disponible.</p>", unsafe_allow_html=True)
    if not is_authenticated():
        st.info("Connectez-vous pour consulter et sauvegarder vos analyses.")
        st.button("Ouvrir Mon compte", type="primary", on_click=go_to, args=("Mon compte",))
        return

    user = current_user()
    analyses = list_analyses(user["id"])
    if not analyses:
        st.info("Aucune analyse sauvegardée pour le moment.")
        st.button("Analyser une propriété", type="primary", on_click=go_to, args=("Analyser",))
        show_alert_center(user, analyses)
        return

    st.caption(f"{len(analyses)} analyse(s) sauvegardée(s) · Les favoris apparaissent en premier.")
    for analysis in analyses:
        favorite = "★ Favori" if analysis["is_favorite"] else "☆"
        label = f"{favorite}  {analysis['property_name']} · dernière mise à jour {analysis['created_at'][:10]}"
        with st.expander(label):
            first, second, third = st.columns(3)
            first.metric("Prix analysé", _money(analysis["price"]))
            second.metric("Flux mensuel", _money(analysis["cash_flow"]))
            third.metric("Score ImmoRadar", f"{analysis['immo_score']:.0f} / 100" if analysis["immo_score"] is not None else "Indisponible")
            st.markdown(
                f"**Date :** {analysis['created_at']}  \n"
                f"**Mise de fonds :** {_money(analysis['down_payment'])}  \n"
                f"**Revenus mensuels :** {_money(analysis['rental_income'])}  \n"
                f"**Dépenses mensuelles :** {_money(analysis['monthly_expenses'])}  \n"
                f"**Couverture de dette :** {analysis['debt_service_coverage_ratio']:.2f}x  \n"
                f"**Moteur :** {analysis['engine_version']}  \n"
                f"**Provenance :** {analysis['data_provenance']}"
            )
            if analysis["immo_score"] is not None:
                st.markdown(
                    f"**Profil ImmoEngine :** {analysis['user_profile']}  \n"
                    f"**Score ImmoRadar :** {analysis['immo_score']:.0f} / 100  \n"
                    f"**Indice de confiance :** {analysis['confidence_index']:.0f} / 100  \n"
                    f"**Verdict :** {analysis['engine_verdict']}"
                )
                positives = json.loads(analysis["positive_factors_json"])
                negatives = json.loads(analysis["negative_factors_json"])
                missing = json.loads(analysis["missing_data_json"])
                if positives:
                    st.write("**Facteurs positifs :** " + " · ".join(positives))
                if negatives:
                    st.write("**Points à surveiller :** " + " · ".join(negatives))
                if missing:
                    st.write("**Données manquantes :** " + " · ".join(missing))
            scenarios = json.loads(analysis.get("scenarios_json", "[]"))
            resilience = json.loads(analysis.get("resilience_json", "{}"))
            if scenarios:
                st.markdown("**Scénarios sauvegardés**")
                st.dataframe([
                    {"Scénario": item["name"], "Flux mensuel": _money(item["financial"]["cash_flow_monthly"]),
                     "DSCR": f"{item['financial']['debt_service_coverage_ratio']:.2f}x", "Verdict": item["engine"]["verdict"]}
                    for item in scenarios
                ], hide_index=True, width="stretch")
            if resilience:
                st.write(f"**Résistance financière :** {resilience.get('status', 'Non calculée')}")
            market_context = json.loads(analysis.get("market_context_json", "[]"))
            if market_context:
                st.markdown("**Contexte de marché observé lors de la sauvegarde**")
                for item in market_context:
                    st.write(f"{item['metric']} : {item['value']} {item['unit']} · observé le {item['observed_at']} · [source officielle]({item['source_url']})")
            # Temporary development access for free accounts; entitlement checks can be added later.
            st.download_button(
                "Télécharger le rapport PDF", generate_report_pdf(analysis),
                file_name=f"immoradar-analyse-{analysis['id']}.pdf", mime="application/pdf",
                key=f"pdf_{analysis['id']}", use_container_width=True,
            )
            actions, delete_column, _ = st.columns([1, 1, 2])
            favorite_label = "Retirer des favoris" if analysis["is_favorite"] else "Ajouter aux favoris"
            if actions.button(favorite_label, key=f"favorite_{analysis['id']}", use_container_width=True):
                toggle_favorite(user["id"], analysis["id"])
                st.rerun()
            if delete_column.button("Supprimer", key=f"delete_{analysis['id']}", use_container_width=True):
                delete_analysis(user["id"], analysis["id"])
                st.rerun()
    show_alert_center(user, analyses)
