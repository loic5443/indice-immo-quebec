"""Presentation of deterministic ImmoEngine results."""

import streamlit as st

from domain.immoengine import ImmoEngineResult


def show_immoengine_result(engine: ImmoEngineResult) -> None:
    """Render the score, confidence, dimensions, and explicit limits."""
    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>IMMOENGINE 1.0</p><h2>Lecture structurée de vos hypothèses</h2>", unsafe_allow_html=True)
    st.info("Ce résultat ne produit aucune estimation de valeur marchande et n'utilise aucune donnée de ville simulée. Il analyse seulement vos hypothèses et les calculs financiers affichés ci-dessus.")
    score_column, confidence_column, verdict_column = st.columns(3)
    score_column.metric("Score ImmoRadar", f"{engine.score:.0f} / 100" if engine.score is not None else "Indisponible")
    confidence_column.metric("Indice de confiance", f"{engine.confidence_index} / 100")
    verdict_column.metric("Verdict", engine.verdict.capitalize())
    st.caption("La confiance mesure la complétude et la qualité des hypothèses saisies; elle n'est pas la probabilité qu'une propriété soit un bon achat.")

    dimension_items = list(engine.dimensions.items())
    for start in range(0, len(dimension_items), 2):
        columns = st.columns(2)
        for column, (_, dimension) in zip(columns, dimension_items[start:start + 2]):
            with column:
                with st.container(border=True):
                    st.markdown(f"### {dimension.label}")
                    if dimension.available:
                        st.metric("Note", f"{dimension.score:.0f} / 100")
                    else:
                        st.caption("Indisponible : données insuffisantes")
                    for factor in dimension.positive_factors:
                        st.success(factor)
                    for factor in dimension.negative_factors:
                        st.warning(factor)
                    for missing in dimension.missing_data:
                        st.caption(f"Donnée manquante : {missing}")

    details, next_steps = st.columns(2)
    with details:
        st.subheader("Facteurs et données manquantes")
        if engine.positive_factors:
            st.markdown("**Facteurs positifs**")
            for factor in engine.positive_factors:
                st.write(f"• {factor}")
        if engine.negative_factors:
            st.markdown("**Points à surveiller**")
            for factor in engine.negative_factors:
                st.write(f"• {factor}")
        if engine.missing_data:
            st.markdown("**Données manquantes**")
            for missing in engine.missing_data:
                st.write(f"• {missing}")
    with next_steps:
        st.subheader("Prochaines vérifications")
        for check in engine.recommended_checks:
            st.write(f"• {check}")
