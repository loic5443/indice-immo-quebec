"""Saved-analysis history, always scoped to the signed-in user."""

import streamlit as st

from components.account import current_user, is_authenticated
from components.sidebar import go_to
from data.database import delete_analysis, list_analyses, toggle_favorite


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def show_saved_analyses() -> None:
    """Show the active user's saved analyses and management actions."""
    st.markdown("<p class='eyebrow'>VOTRE HISTORIQUE</p><h1>Mes analyses</h1>", unsafe_allow_html=True)
    if not is_authenticated():
        st.info("Connectez-vous pour consulter et sauvegarder vos analyses.")
        st.button("Ouvrir Mon compte", type="primary", on_click=go_to, args=("Mon compte",))
        return

    user = current_user()
    analyses = list_analyses(user["id"])
    if not analyses:
        st.info("Aucune analyse sauvegardée pour le moment.")
        st.button("Créer une analyse", type="primary", on_click=go_to, args=("Analyse immobilière",))
        return

    st.caption(f"{len(analyses)} analyse(s) sauvegardée(s) · Les favoris apparaissent en premier.")
    for analysis in analyses:
        favorite = "★ Favori" if analysis["is_favorite"] else "☆"
        label = f"{favorite}  {analysis['property_name']} · {_money(analysis['price'])}"
        with st.expander(label):
            first, second, third = st.columns(3)
            first.metric("Flux mensuel", _money(analysis["cash_flow"]))
            second.metric("Rendement annuel", f"{analysis['cash_on_cash_return']:.2f} %")
            third.metric("Capitalisation", f"{analysis['capitalization_rate']:.2f} %")
            st.markdown(
                f"**Date :** {analysis['created_at']}  \n"
                f"**Mise de fonds :** {_money(analysis['down_payment'])}  \n"
                f"**Revenus mensuels :** {_money(analysis['rental_income'])}  \n"
                f"**Dépenses mensuelles :** {_money(analysis['monthly_expenses'])}  \n"
                f"**Couverture de dette :** {analysis['debt_service_coverage_ratio']:.2f}x  \n"
                f"**Moteur :** {analysis['engine_version']}  \n"
                f"**Provenance :** {analysis['data_provenance']}"
            )
            actions, delete_column, _ = st.columns([1, 1, 2])
            favorite_label = "Retirer des favoris" if analysis["is_favorite"] else "Ajouter aux favoris"
            if actions.button(favorite_label, key=f"favorite_{analysis['id']}", use_container_width=True):
                toggle_favorite(user["id"], analysis["id"])
                st.rerun()
            if delete_column.button("Supprimer", key=f"delete_{analysis['id']}", use_container_width=True):
                delete_analysis(user["id"], analysis["id"])
                st.rerun()
