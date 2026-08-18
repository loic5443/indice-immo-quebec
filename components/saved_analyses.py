"""Saved-analysis history, always scoped to the signed-in user."""

import json
import streamlit as st

from components.account import current_user, is_authenticated
from components.sidebar import go_to
from components.alerts import show_alert_center
from data.database import DATABASE_PATH, delete_analysis, list_analyses, toggle_favorite
from services.entitlements_service import can_use
from services.property_comparison_service import ComparisonAccessError, compare_saved_analyses
from services.report_service import generate_comparison_report_pdf, generate_report_pdf


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def _comparison_value(key: str, value: float | None) -> str:
    """Format a stored value without replacing an absence with a misleading zero."""
    if value is None:
        return "Non disponible"
    if key in {"cash_on_cash_return", "capitalization_rate"}:
        return f"{value:.2f} %"
    if key == "dscr":
        return f"{value:.2f}x"
    if key in {"score", "confidence", "immovalue_confidence"}:
        return f"{value:.0f} / 100"
    return _money(value)


def _analysis_label(analysis: dict) -> str:
    date = str(analysis.get("created_at", ""))[:10] or "date inconnue"
    return f"{analysis.get('property_name') or 'Dossier sans nom'} · {date}"


def _show_comparison_metric(label: str, value_a: str, value_b: str, relation: str | None = None) -> None:
    """Keep each indicator narrow and readable on a phone."""
    with st.container(border=True):
        st.markdown(f"**{label}**")
        first, second = st.columns(2)
        first.caption("Propriété A")
        first.write(value_a)
        second.caption("Propriété B")
        second.write(value_b)
        relation_labels = {
            "avantage_a": "Avantage A selon les instantanés",
            "avantage_b": "Avantage B selon les instantanés",
            "égalité": "Équivalent selon les instantanés",
            "non_comparable": "Non comparable avec les données sauvegardées",
        }
        if relation:
            st.caption(relation_labels[relation])


def _show_property_comparator(user: dict, analyses: list[dict]) -> None:
    """Render the comparator; storage access remains scoped in the service query."""
    st.markdown("<div class='section-space compact-space'></div><h2>Comparer deux propriétés</h2>", unsafe_allow_html=True)
    if len(analyses) < 2:
        st.info("Sauvegardez au moins deux dossiers pour les comparer ici. Chaque dossier reste privé à votre compte.")
        return

    labels = {int(analysis["id"]): _analysis_label(analysis) for analysis in analyses}
    ids = list(labels)
    st.caption("Comparez deux instantanés sauvegardés. Les calculs d’origine ne sont jamais refaits ni modifiés.")
    first, second, reset = st.columns([5, 5, 2])
    with first:
        selected_a = st.selectbox("Propriété A", ids, format_func=labels.__getitem__, key="comparison_property_a")
    with second:
        selected_b = st.selectbox("Propriété B", ids, index=1, format_func=labels.__getitem__, key="comparison_property_b")
    with reset:
        st.write("")
        if st.button("Réinitialiser", key="comparison_reset", use_container_width=True):
            st.session_state.pop("comparison_property_a", None)
            st.session_state.pop("comparison_property_b", None)
            st.rerun()

    if selected_a == selected_b:
        st.error("Choisissez deux dossiers différents.")
        return
    try:
        comparison = compare_saved_analyses(user["id"], selected_a, selected_b, str(DATABASE_PATH))
    except (ComparisonAccessError, ValueError):
        # Do not reveal whether a requested ID belongs to another user.
        st.error("Ces dossiers ne sont pas disponibles dans votre espace.")
        return

    header_a, header_b = st.columns(2)
    for column, key, label in ((header_a, "a", "Propriété A"), (header_b, "b", "Propriété B")):
        snapshot = comparison[key]
        with column:
            st.markdown(f"<p class='eyebrow'>{label.upper()}</p>", unsafe_allow_html=True)
            st.subheader(snapshot["name"])
            st.caption(f"Analyse du {snapshot['date']} · {snapshot['property_type'] or 'Type non précisé'}")

    if not can_use(user, "advanced_comparisons"):
        st.markdown("<section class='premium-notice'><p class='eyebrow'>APERÇU GRATUIT</p><h3>Les repères essentiels de vos deux dossiers</h3><p>Premium ajoute les indicateurs financiers, les scénarios et la lecture comparative expliquée.</p></section>", unsafe_allow_html=True)
        for item in comparison["indicators"]:
            if item["key"] in {"price", "cash_flow", "score", "confidence"}:
                _show_comparison_metric(item["label"], _comparison_value(item["key"], item["a"]), _comparison_value(item["key"], item["b"]), item["relation"])
        st.button("Découvrir Premium", on_click=go_to, args=("Premium",), key="comparison_premium")
        return

    st.success("Comparaison complète basée sur les instantanés sauvegardés.")
    st.download_button(
        "Télécharger le rapport comparatif PDF", generate_comparison_report_pdf(comparison),
        file_name="immoradar-comparaison.pdf", mime="application/pdf",
        key="comparison_pdf", use_container_width=True,
    )
    for item in comparison["indicators"]:
        value_a = _comparison_value(item["key"], item["a"])
        value_b = _comparison_value(item["key"], item["b"])
        if item["key"] == "municipal_value":
            if item["a"] is not None:
                value_a += f" · rôle {comparison['a']['municipal_role_year'] or 'année non précisée'}"
            if item["b"] is not None:
                value_b += f" · rôle {comparison['b']['municipal_role_year'] or 'année non précisée'}"
        if item["key"] == "immovalue":
            if item["a"] is not None:
                value_a += f" · {_comparison_value('price', comparison['a']['immovalue_low'])} à {_comparison_value('price', comparison['a']['immovalue_high'])}"
            if item["b"] is not None:
                value_b += f" · {_comparison_value('price', comparison['b']['immovalue_low'])} à {_comparison_value('price', comparison['b']['immovalue_high'])}"
        _show_comparison_metric(item["label"], value_a, value_b, item["relation"])

    st.markdown("### Scénarios sauvegardés")
    for scenario in comparison["scenarios"].values():
        _show_comparison_metric(scenario["label"], _comparison_value("cash_flow", scenario["a"]), _comparison_value("cash_flow", scenario["b"]))

    st.markdown("### Ce qui distingue chaque propriété")
    strengths_a, strengths_b = st.columns(2)
    for column, key, title in ((strengths_a, "a", "Propriété A"), (strengths_b, "b", "Propriété B")):
        with column:
            st.markdown(f"**{title}**")
            for item in comparison["strengths"][key] or ["Aucun avantage net n’est établi avec les instantanés disponibles."]:
                st.write(f"• {item}")
            st.caption("À vérifier")
            for item in comparison["checks"][key] or ["Aucune donnée manquante signalée parmi les indicateurs comparés."]:
                st.write(f"• {item}")
    st.info(comparison["conclusion"])
    if comparison["engine_versions_differ"]:
        st.warning("Les versions d’ImmoEngine diffèrent entre les dossiers. Les valeurs sont comparées telles qu’elles ont été sauvegardées.")
    with st.expander("Méthode et limites"):
        st.write("Le comparateur lit uniquement les instantanés déjà sauvegardés. Il ne recalcule ni ImmoScore, ni ImmoValue, ni vos scénarios. Une donnée absente reste non disponible.")
        st.write("La valeur municipale est un repère fiscal, distinct d’une estimation de valeur marchande. Cette comparaison n’est pas une recommandation d’achat.")


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
    analyses = list_analyses(user["id"], DATABASE_PATH)
    if not analyses:
        st.info("Aucune analyse sauvegardée pour le moment.")
        st.button("Analyser une propriété", type="primary", on_click=go_to, args=("Analyser",))
        show_alert_center(user, analyses)
        return

    st.caption(f"{len(analyses)} analyse(s) sauvegardée(s) · Les favoris apparaissent en premier.")
    _show_property_comparator(user, analyses)
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
                toggle_favorite(user["id"], analysis["id"], DATABASE_PATH)
                st.rerun()
            if delete_column.button("Supprimer", key=f"delete_{analysis['id']}", use_container_width=True):
                delete_analysis(user["id"], analysis["id"], DATABASE_PATH)
                st.rerun()
    show_alert_center(user, analyses)
