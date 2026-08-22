"""Saved-analysis history, always scoped to the signed-in user."""

import json
import streamlit as st

from components.account import current_user, is_authenticated
from components.sidebar import go_to
from components.alerts import show_alert_center
from components.premium_teaser import show_premium_teaser
from data.database import DATABASE_PATH, delete_analysis, list_analyses, toggle_favorite
from services.alert_service import build_calculable_alerts
from services.entitlements_service import can_use
from services.property_comparison_service import ComparisonAccessError, compare_saved_analyses
from services.analysis_reopen_service import AnalysisReopenAccessError, prepare_reopen_draft
from services.dossier_tracking_service import (
    DossierTrackingAccessError,
    dossier_fingerprint,
    filter_tracked_analyses,
    set_dossier_tracking,
    tracked_dossier_fingerprints,
)
from services.report_service import generate_comparison_report_pdf, generate_report_pdf
from services.snapshot_history_service import snapshot_positions


DELETE_CONFIRMATION_KEY = "pending_analysis_delete"
ACTION_FEEDBACK_KEY = "saved_analysis_action_feedback"


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


def _saved_asking_price(analysis: dict) -> float | None:
    """Read only the declared subject amount from an analysis snapshot."""

    try:
        payload = json.loads(analysis.get("immovalue_json") or "{}")
        value = payload.get("subject", {}).get("asking_price") if isinstance(payload, dict) else None
        return float(value) if isinstance(value, (int, float)) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _saved_official_role(analysis: dict) -> dict | None:
    """Read a public fiscal snapshot without treating it as market value."""

    try:
        snapshot = json.loads(analysis.get("official_role_snapshot_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("total_value"), (int, float)):
        return None
    return snapshot


def _snapshot_history_rows(snapshots: tuple[dict, ...]) -> list[dict[str, str]]:
    """Prepare a compact timeline from immutable values already saved by the user."""

    rows: list[dict[str, str]] = []
    for snapshot in snapshots[:5]:
        role = _saved_official_role(snapshot)
        score = snapshot.get("immo_score")
        cash_flow = snapshot.get("cash_flow")
        rows.append({
            "Date": str(snapshot.get("created_at") or "")[:10] or "Non publiée",
            "Flux mensuel": _money(cash_flow) if isinstance(cash_flow, (int, float)) else "Non disponible",
            "Score": f"{float(score):.0f} / 100" if isinstance(score, (int, float)) else "Non disponible",
            "Rôle municipal": _money(role["total_value"]) if role else "Non disponible",
        })
    return rows


def _filter_saved_analyses(
    analyses: list[dict], query: str, scope: str, sort_by: str, tracked_fingerprints: set[str], user_id: int,
) -> list[dict]:
    """Filter only the already owner-scoped list; names never leave the session."""

    query = query.strip().casefold()
    filtered = [
        analysis for analysis in analyses
        if not query or query in str(analysis.get("property_name") or "").casefold()
    ]
    if scope == "Favoris":
        filtered = [analysis for analysis in filtered if bool(analysis.get("is_favorite"))]
    elif scope == "Suivis":
        filtered = [
            analysis for analysis in filtered
            if dossier_fingerprint(user_id, analysis.get("property_name")) in tracked_fingerprints
        ]

    if sort_by == "Plus ancien":
        return sorted(filtered, key=lambda item: (str(item.get("created_at") or ""), int(item.get("id") or 0)))
    if sort_by == "Score le plus élevé":
        return sorted(
            filtered,
            key=lambda item: (item.get("immo_score") is None, -(float(item.get("immo_score") or 0)), -int(item.get("id") or 0)),
        )
    if sort_by == "Favoris puis récents":
        return sorted(
            filtered,
            key=lambda item: (int(bool(item.get("is_favorite"))), str(item.get("created_at") or ""), int(item.get("id") or 0)),
            reverse=True,
        )
    return sorted(filtered, key=lambda item: (str(item.get("created_at") or ""), int(item.get("id") or 0)), reverse=True)


def _reset_saved_analysis_filters() -> None:
    """Reset only local UI state, never a saved dossier or follow choice."""

    st.session_state["saved_analysis_search"] = ""
    st.session_state["saved_analysis_scope"] = "Tous"
    st.session_state["saved_analysis_sort"] = "Favoris puis récents"


def _request_analysis_deletion(user_id: int, analysis_id: int) -> None:
    """Stage one owner-scoped deletion; the next explicit click confirms it."""

    st.session_state[DELETE_CONFIRMATION_KEY] = {"owner_id": user_id, "analysis_id": analysis_id}


def _cancel_analysis_deletion() -> None:
    st.session_state.pop(DELETE_CONFIRMATION_KEY, None)


def _set_action_feedback(message: str) -> None:
    """Persist a short confirmation through the intentional Streamlit rerun."""

    st.session_state[ACTION_FEEDBACK_KEY] = message


def _show_action_feedback() -> None:
    """Display a one-time, local confirmation without retaining dossier data."""

    message = st.session_state.pop(ACTION_FEEDBACK_KEY, None)
    if isinstance(message, str) and message:
        st.success(message)


def _tracking_overview(analyses: list[dict]) -> dict[str, int]:
    """Count only alerts that can be proved from followed saved snapshots."""

    alerts = build_calculable_alerts(analyses)
    return {
        "total": len(alerts),
        "important": sum(alert["severity"] == "important" for alert in alerts),
        "updates": sum(alert["severity"] == "info" for alert in alerts),
    }


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
        st.markdown("<p class='eyebrow'>APERÇU GRATUIT</p><div class='notice-title' role='heading' aria-level='3'>Les repères essentiels de vos deux dossiers</div>", unsafe_allow_html=True)
        for item in comparison["indicators"]:
            if item["key"] in {"price", "cash_flow", "score", "confidence"}:
                _show_comparison_metric(item["label"], _comparison_value(item["key"], item["a"]), _comparison_value(item["key"], item["b"]), item["relation"])
        show_premium_teaser(
            feature="Lecture comparative détaillée",
            title="Comparez ce qui change vraiment entre vos deux dossiers.",
            detail="Premium affiche les dépenses, revenus, scénarios, taux de capitalisation et capacité à couvrir la dette à partir de vos instantanés sauvegardés.",
            key="comparison_premium",
        )
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
    _show_action_feedback()
    analyses = list_analyses(user["id"], DATABASE_PATH)
    if not analyses:
        st.markdown(
            "<div class='account-summary'><p class='eyebrow'>VOTRE PREMIER DOSSIER</p>"
            "<div class='notice-title' role='heading' aria-level='2'>Vous n’avez encore aucun dossier sauvegardé.</div>"
            "<p>Commencez par une propriété, ajoutez seulement les chiffres que vous connaissez, puis sauvegardez "
            "la synthèse pour y revenir, la comparer ou la suivre.</p></div>",
            unsafe_allow_html=True,
        )
        st.button("Créer mon premier dossier", type="primary", on_click=go_to, args=("Analyser",), use_container_width=True)
        show_alert_center(user, analyses)
        return

    tracked_fingerprints = tracked_dossier_fingerprints(user["id"], DATABASE_PATH)
    tracked_analyses = filter_tracked_analyses(user["id"], analyses, DATABASE_PATH)
    favorite_count = sum(bool(item.get("is_favorite")) for item in analyses)
    followed_count = len({dossier_fingerprint(user["id"], item["property_name"]) for item in tracked_analyses})
    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>VOTRE ESPACE</p><div class='section-title' role='heading' aria-level='2'>Vos dossiers en un coup d’œil.</div>", unsafe_allow_html=True)
    saved_column, favorite_column, followed_column, action_column = st.columns([1, 1, 1, 1.3])
    saved_column.metric("Dossiers sauvegardés", len(analyses))
    favorite_column.metric("Favoris", favorite_count)
    followed_column.metric("Suivis", followed_count)
    with action_column:
        st.write("")
        st.button("Créer un nouveau dossier", type="primary", on_click=go_to, args=("Analyser",), key="saved_new_analysis", use_container_width=True)
    st.caption(f"{followed_count} dossier(s) suivi(s) · Les favoris apparaissent en premier. Le suivi lit uniquement les instantanés sauvegardés et n’envoie aucun courriel pendant la bêta.")
    if can_use(user, "alerts"):
        overview = _tracking_overview(tracked_analyses)
        st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>SUIVI ACTIF</p><h2>Ce qui mérite votre attention</h2>", unsafe_allow_html=True)
        all_alerts, important_alerts, updates = st.columns(3)
        all_alerts.metric("Alertes calculables", overview["total"])
        important_alerts.metric("À vérifier", overview["important"])
        updates.metric("Mises à jour", overview["updates"])
        st.caption("Ces compteurs lisent uniquement vos instantanés suivis. Ils ne prévoient rien et ne déclenchent aucun envoi.")
    _show_property_comparator(user, analyses)
    history_by_id = snapshot_positions(analyses)
    st.markdown("<div class='section-space compact-space'></div><h2>Vos dossiers</h2>", unsafe_allow_html=True)
    search_column, scope_column, sort_column, reset_column = st.columns([4, 2, 2, 1])
    with search_column:
        query = st.text_input("Rechercher un dossier", placeholder="Nom ou adresse déjà sauvegardé", key="saved_analysis_search")
    with scope_column:
        scope = st.selectbox("Afficher", ["Tous", "Favoris", "Suivis"], key="saved_analysis_scope")
    with sort_column:
        sort_by = st.selectbox("Trier", ["Favoris puis récents", "Plus récent", "Plus ancien", "Score le plus élevé"], key="saved_analysis_sort")
    with reset_column:
        st.write("")
        st.button("Effacer", key="reset_saved_analysis_filters", on_click=_reset_saved_analysis_filters, use_container_width=True)
    displayed_analyses = _filter_saved_analyses(analyses, query, scope, sort_by, tracked_fingerprints, user["id"])
    st.caption(f"{len(displayed_analyses)} dossier(s) affiché(s). La recherche reste dans cette session et n’est jamais envoyée à un service externe.")
    if not displayed_analyses:
        st.info("Aucun dossier ne correspond à ces filtres.")
    for analysis in displayed_analyses:
        favorite = "★ Favori" if analysis["is_favorite"] else "☆"
        label = f"{favorite}  {analysis['property_name']} · dernière mise à jour {analysis['created_at'][:10]}"
        with st.expander(label):
            history = history_by_id.get(int(analysis["id"]))
            if history and history.total > 1:
                status = "Dernier instantané" if history.is_latest else f"Instantané {history.position}"
                st.caption(
                    f"{status} sur {history.total} pour ce dossier. Les alertes Premium comparent uniquement "
                    "ces versions sauvegardées, sans refaire vos calculs."
                )
                with st.container(border=True):
                    st.markdown("**Historique des instantanés**")
                    st.dataframe(_snapshot_history_rows(history.snapshots), hide_index=True, width="stretch")
                    st.caption("Les montants et scores sont ceux sauvegardés à chaque date. Une donnée absente reste non disponible.")
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
            asking_price = _saved_asking_price(analysis)
            if asking_price is not None:
                st.caption(f"Prix demandé déclaré : {_money(asking_price)} · distinct de la valeur municipale et d’ImmoValue.")
            official_role = _saved_official_role(analysis)
            if official_role:
                reference = official_role.get("reference_date") or "date de référence non publiée"
                st.caption(
                    f"Valeur au rôle municipal sauvegardée : {_money(official_role['total_value'])} · "
                    f"rôle {official_role.get('role_year') or 'année non publiée'} · {reference}. "
                    "Repère fiscal officiel, distinct d’une valeur marchande."
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
            if can_use(user, "reports"):
                st.download_button(
                    "Télécharger le rapport PDF", generate_report_pdf(analysis),
                    file_name=f"immoradar-analyse-{analysis['id']}.pdf", mime="application/pdf",
                    key=f"pdf_{analysis['id']}", use_container_width=True,
                )
            else:
                show_premium_teaser(
                    feature="Rapport PDF complet",
                    title="Gardez une lecture complète de votre dossier.",
                    detail="Premium regroupe les calculs, scénarios, score, limites et sources déjà sauvegardés dans un rapport exportable.",
                    key=f"report_premium_{analysis['id']}",
                )
            open_column, follow_column, favorite_column, delete_column = st.columns(4)
            if open_column.button("Ouvrir et modifier", key=f"reopen_{analysis['id']}", use_container_width=True):
                try:
                    st.session_state["analysis_reopen_pending"] = prepare_reopen_draft(
                        user["id"], int(analysis["id"]), DATABASE_PATH,
                    )
                except AnalysisReopenAccessError:
                    st.error("Ce dossier n’est pas disponible dans votre espace.")
                else:
                    go_to("Analyser")
                    st.rerun()
            fingerprint = dossier_fingerprint(user["id"], analysis["property_name"])
            followed = fingerprint in tracked_fingerprints
            if can_use(user, "alerts"):
                follow_label = "Arrêter le suivi" if followed else "Suivre ce dossier"
                if follow_column.button(follow_label, key=f"follow_{analysis['id']}", use_container_width=True):
                    try:
                        set_dossier_tracking(user["id"], int(analysis["id"]), not followed, DATABASE_PATH)
                    except DossierTrackingAccessError:
                        st.error("Ce dossier n’est pas disponible dans votre espace.")
                    else:
                        _set_action_feedback("Suivi activé." if not followed else "Suivi arrêté.")
                        st.rerun()
            else:
                follow_column.button("Suivi Premium", key=f"follow_locked_{analysis['id']}", disabled=True, use_container_width=True)
            favorite_label = "Retirer des favoris" if analysis["is_favorite"] else "Ajouter aux favoris"
            if favorite_column.button(favorite_label, key=f"favorite_{analysis['id']}", use_container_width=True):
                toggle_favorite(user["id"], analysis["id"], DATABASE_PATH)
                _set_action_feedback("Dossier ajouté aux favoris." if not analysis["is_favorite"] else "Dossier retiré des favoris.")
                st.rerun()
            pending_deletion = st.session_state.get(DELETE_CONFIRMATION_KEY)
            deletion_requested = (
                isinstance(pending_deletion, dict)
                and pending_deletion.get("owner_id") == user["id"]
                and pending_deletion.get("analysis_id") == analysis["id"]
            )
            if deletion_requested:
                delete_column.warning("Confirmer la suppression de ce dossier et de son historique ?")
                confirm, cancel = delete_column.columns(2)
                if confirm.button("Confirmer", key=f"confirm_delete_{analysis['id']}", type="primary", use_container_width=True):
                    if delete_analysis(user["id"], analysis["id"], DATABASE_PATH):
                        _cancel_analysis_deletion()
                        _set_action_feedback("Dossier supprimé.")
                        st.rerun()
                    else:
                        st.error("Ce dossier n’est plus disponible dans votre espace.")
                if cancel.button("Annuler", key=f"cancel_delete_{analysis['id']}", use_container_width=True):
                    _cancel_analysis_deletion()
                    st.rerun()
            elif delete_column.button("Supprimer", key=f"delete_{analysis['id']}", use_container_width=True):
                _request_analysis_deletion(user["id"], analysis["id"])
                st.rerun()
    show_alert_center(user, tracked_analyses, tracking_configured=True)
