"""Commercial landing page for ImmoRadar."""

import streamlit as st

from components.sidebar import go_to


def show_home() -> None:
    st.markdown(
        """
        <section class="hero-panel">
          <p class="eyebrow">DECIDEZ AVEC CLARTE</p>
          <h1>Votre prochain projet immobilier,<br>vu avec les bons chiffres.</h1>
          <p class="hero-copy">ImmoRadar transforme vos hypothèses de financement, revenus et dépenses en une analyse simple, lisible et concrète.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    primary, secondary, _ = st.columns([1, 1, 3])
    primary.button("Analyser une propriété", type="primary", on_click=go_to, args=("Analyse immobilière",), use_container_width=True)
    secondary.button("Découvrir Premium", on_click=go_to, args=("Premium",), use_container_width=True)

    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    st.markdown("<p class='eyebrow'>POURQUOI IMMORADAR</p><h2>Une analyse qui vous aide à poser les bonnes questions.</h2>", unsafe_allow_html=True)
    benefits = st.columns(3)
    benefit_content = [
        ("Financement clair", "Visualisez immédiatement le prêt, le paiement mensuel et la pression sur votre budget."),
        ("Rentabilité lisible", "Mesurez le flux de trésorerie, le rendement sur la mise et le taux de capitalisation."),
        ("Décision transparente", "Distinguez vos hypothèses, les calculs et les données de marché avant de vous engager."),
    ]
    for column, (title, copy) in zip(benefits, benefit_content):
        with column:
            with st.container(border=True):
                st.markdown(f"<div class='feature-icon'>◆</div><h3>{title}</h3><p class='muted-copy'>{copy}</p>", unsafe_allow_html=True)

    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    st.markdown("<p class='eyebrow'>VOS OUTILS</p><h2>Tout l’essentiel pour évaluer un projet.</h2>", unsafe_allow_html=True)
    features = st.columns(4)
    feature_content = [
        ("Analyse", "Hypothèses, financement et dépenses réunis au même endroit."),
        ("Flux mensuel", "Voyez ce que le projet produit réellement chaque mois."),
        ("Ratios", "Rendement, capitalisation et couverture de dette expliqués."),
        ("Marchés", "Repères et tendances pour situer votre analyse."),
    ]
    for column, (title, copy) in zip(features, feature_content):
        with column:
            st.markdown(f"<div class='mini-feature'><h3>{title}</h3><p>{copy}</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("<p class='eyebrow'>TRANSPARENCE DES DONNEES</p><h2>Ce que vous voyez, clairement identifié.</h2>", unsafe_allow_html=True)
        st.write("Vos chiffres de projet sont vos propres hypothèses. Les formules financières sont calculées dans l’application et restent distinctes des données de marché.")
    with right:
        with st.container(border=True):
            st.markdown("**Donnée réelle lorsque disponible**")
            st.write("Taux directeur de la Banque du Canada.")
            st.markdown("**Données simulées**")
            st.write("Inflation, chômage, prix, variations et historiques par ville.")

    st.markdown("<div class='final-cta'><p class='eyebrow'>PRET A COMMENCER</p><h2>Évaluez votre prochaine propriété avec plus de confiance.</h2></div>", unsafe_allow_html=True)
    final_col, _ = st.columns([1, 3])
    final_col.button("Ouvrir l'analyse immobilière", type="primary", on_click=go_to, args=("Analyse immobilière",), use_container_width=True)
