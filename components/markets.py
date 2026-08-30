"""Honest municipal comparisons based only on loaded official datasets."""

from __future__ import annotations

import streamlit as st

from data.database import DATABASE_PATH
from components.sidebar import go_to
from services.municipal_comparison_service import comparison, municipalities, selection_options


LABELS = {
    "population": (
        "Population", "habitants",
        "Indique la taille démographique; elle ne mesure pas la demande immobilière.",
    ),
    "uniformized_residential_assessment_average": (
        "Valeur foncière moyenne uniformisée résidentielle", "$",
        "Repère fiscal officiel; ce n’est pas le prix moyen des ventes actuelles.",
    ),
    "uniformized_property_wealth": (
        "Richesse foncière uniformisée", "$",
        "Indicateur municipal global; il ne prédit pas une valeur de propriété.",
    ),
    "uniformized_property_wealth_per_unit": (
        "RFU par unité", "$ par unité",
        "Repère de fiscalité municipale; il ne mesure pas un rendement locatif.",
    ),
}


def _reset_municipal_selection() -> None:
    st.session_state["municipal_selected"] = []
    st.session_state["municipal_search"] = ""


def _format_value(value: float, unit: str) -> str:
    return f"{value:,.0f} {unit}".replace(",", " ")


def _indicator_rows(rows: list[dict], indicator_code: str) -> list[dict]:
    """Return one official indicator in a stable municipal order for display."""

    return sorted(
        (row for row in rows if row["indicator_code"] == indicator_code),
        key=lambda row: str(row["municipality_name"]).casefold(),
    )


def _show_reading_guide() -> None:
    understands, does_not = st.columns(2)
    with understands:
        st.markdown(
            "<article class='benefit-card'><div class='card-title' role='heading' aria-level='2'>Ce que vous comparez</div>"
            "<p>Des indicateurs municipaux publiés par le MAMH, à une année commune, pour situer deux à quatre territoires.</p>"
            "</article>",
            unsafe_allow_html=True,
        )
    with does_not:
        st.markdown(
            "<article class='benefit-card'><div class='card-title' role='heading' aria-level='2'>Ce que cela ne dit pas</div>"
            "<p>Ni le prix de vente d’une propriété, ni son rendement, ni son niveau de risque. Ces données restent indisponibles sans source autorisée.</p>"
            "</article>",
            unsafe_allow_html=True,
        )


def _show_indicator(rows: list[dict], code: str) -> None:
    """Present an official indicator without calculating an unsupported ratio."""

    label, unit, explanation = LABELS[code]
    st.markdown(f"### {label}")
    st.caption(explanation)
    display_rows = _indicator_rows(rows, code)
    columns = st.columns(min(len(display_rows), 4))
    for column, row in zip(columns, display_rows):
        with column:
            st.metric(row["municipality_name"], _format_value(float(row["value"]), unit))
    st.bar_chart(
        {row["municipality_name"]: float(row["value"]) for row in display_rows},
        horizontal=True,
        width="stretch",
    )
    st.caption("Visualisation des données officielles sélectionnées; elle n’ajoute aucune estimation.")


def show_markets() -> None:
    st.markdown("<p class='eyebrow'>MARCHÉ</p>", unsafe_allow_html=True)
    st.title("Comparer les municipalités")
    st.markdown(
        "<p class='section-intro'>Des repères municipaux officiels pour situer un territoire, sans prix de vente, rendement ou risque inventés.</p>",
        unsafe_allow_html=True,
    )
    _show_reading_guide()
    all_municipalities = municipalities(DATABASE_PATH)
    if not all_municipalities:
        st.warning(
            "La comparaison municipale officielle n’est pas encore disponible dans cet environnement. "
            "ImmoRadar n’affiche aucune valeur de remplacement et ne crée aucun indicateur de marché sans source autorisée."
        )
        st.markdown(
            "<div class='account-summary'><p class='eyebrow'>EN ATTENDANT</p>"
            "<div class='notice-title' role='heading' aria-level='2'>Analysez une propriété avec les renseignements disponibles.</div>"
            "<p>Vous pouvez révéler un rôle municipal lorsqu’il est disponible, ajouter vos chiffres et sauvegarder votre dossier. "
            "La comparaison entre municipalités apparaîtra ici seulement lorsque les mêmes indicateurs officiels pourront être comparés honnêtement.</p></div>",
            unsafe_allow_html=True,
        )
        st.button("Analyser une propriété", type="primary", on_click=go_to, args=("Analyser",), key="markets_empty_analysis")
        return

    st.info(
        "Commencez par rechercher une municipalité, puis ajoutez-en une deuxième pour comparer les repères "
        "officiels disponibles à une année commune."
    )
    available, selected_count, limit = st.columns(3)
    available.metric("Municipalités disponibles", len(all_municipalities))
    selected_count.metric("Municipalités sélectionnées", f"{len(st.session_state.get('municipal_selected', []))} / 4")
    limit.metric("Comparaison utile", "2 à 4 villes")

    query = st.text_input(
        "Rechercher et ajouter une municipalité", key="municipal_search", placeholder="Ex. Montréal",
    )
    current = st.session_state.get("municipal_selected", [])
    choices = selection_options(current, municipalities(DATABASE_PATH, query))
    selected = st.multiselect(
        "Sélectionnez de deux à quatre municipalités", choices, max_selections=4,
        key="municipal_selected", placeholder="Choisir des municipalités",
        help="Une recherche ne retire jamais les municipalités que vous avez déjà choisies.",
    )
    st.caption("Votre recherche ne retire jamais les municipalités déjà sélectionnées.")
    st.button("Réinitialiser la comparaison", on_click=_reset_municipal_selection, width="stretch")

    result = comparison(DATABASE_PATH, selected)
    if not result["available"]:
        missing = result.get("missing", [])
        if missing and len(selected) >= 2:
            st.info(
                "Les données officielles sont incomplètes pour : " + ", ".join(missing) + ". "
                "Choisissez des municipalités couvertes par les mêmes indicateurs et la même année; "
                "aucune valeur manquante n’est remplacée par zéro."
            )
        else:
            st.info(
                "Sélectionnez au moins deux municipalités couvertes par la même année. Les données manquantes restent "
                "indiquées comme indisponibles et ne sont jamais remplacées par zéro."
            )
        return

    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>COMPARAISON OFFICIELLE</p>", unsafe_allow_html=True)
    st.caption(
        f"Données officielles disponibles · année commune : {result['year']} · Source : MAMH, Profil financier des municipalités locales, "
        "CC-BY 4.0 · données récupérées localement."
    )
    available_codes = [code for code in LABELS if _indicator_rows(result["rows"], code)]
    selected_indicator = st.selectbox(
        "Repère à visualiser", available_codes,
        format_func=lambda code: LABELS[code][0], key="municipal_indicator_view",
    )
    _show_indicator(result["rows"], selected_indicator)

    with st.expander("Voir tous les repères officiels"):
        table_rows = [
            {
                "Indicateur": LABELS[row["indicator_code"]][0],
                "Municipalité": row["municipality_name"],
                "Valeur": _format_value(float(row["value"]), LABELS[row["indicator_code"]][1]),
                "Année": row["year"],
            }
            for row in result["rows"]
        ]
        st.dataframe(table_rows, hide_index=True, width="stretch")
        st.caption("Chaque ligne est une donnée officielle attribuée au MAMH/Données Québec.")
