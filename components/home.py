"""Landing page content for ImmoRadar."""

import base64
from pathlib import Path

import streamlit as st

from components.sidebar import go_to


HERO_IMAGE_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "images" / "immoradar-hero.png"
)


@st.cache_data(show_spinner=False)
def _hero_image_style() -> str:
    """Return a local, offline-safe hero background as a data URI.

    The CSS gradient remains a readable fallback if the local asset is absent.
    """
    if not HERO_IMAGE_PATH.is_file():
        return ""

    encoded_image = base64.b64encode(HERO_IMAGE_PATH.read_bytes()).decode("ascii")
    return (
        "background-image: "
        "linear-gradient(90deg, rgba(7, 23, 45, 0.96) 0%, "
        "rgba(10, 33, 62, 0.88) 43%, rgba(10, 27, 48, 0.38) 100%), "
        f"url('data:image/png;base64,{encoded_image}');"
    )


def show_home() -> None:
    """Display the commercial home page and links to the product areas."""
    st.markdown(
        f"""
        <section class="hero-image-panel" style="{_hero_image_style()}">
          <div class="hero-content">
            <p class="hero-eyebrow">IMMOBILIER INTELLIGENT</p>
            <h1>Votre prochain projet immobilier mérite plus qu'une intuition.</h1>
            <p class="hero-copy">ImmoRadar transforme vos hypothèses de financement,
            revenus et dépenses en une analyse concrète, lisible et prête à éclairer votre décision.</p>
            <div class="hero-proof">
              <span>Analyse complète</span><span>Calculs transparents</span><span>Décision mieux informée</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    primary, secondary, _ = st.columns([1.15, 1.05, 2.8])
    primary.button(
        "Analyser une propriété",
        type="primary",
        on_click=go_to,
        args=("Analyse immobilière",),
        use_container_width=True,
    )
    secondary.button(
        "Découvrir Premium",
        on_click=go_to,
        args=("Premium",),
        use_container_width=True,
    )

    st.markdown("<div class='section-space compact-space'></div>", unsafe_allow_html=True)
    stat_columns = st.columns(3)
    stat_content = [
        ("10", "hypothèses clés", "Financement, dépenses et revenus réunis dans une même analyse."),
        ("4", "indicateurs décisifs", "Flux mensuel, rendement, capitalisation et couverture de dette."),
        ("1", "lecture plus claire", "Vos données, les calculs et les repères de marché restent distincts."),
    ]
    for column, (value, label, copy) in zip(stat_columns, stat_content):
        with column:
            st.markdown(
                f"<div class='stat-card'><strong>{value}</strong><span>{label}</span><p>{copy}</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p class='eyebrow'>COMMENT ÇA FONCTIONNE</p>"
        "<h2>Trois étapes pour voir votre projet avec plus de recul.</h2>"
        "<p class='section-intro'>Vous gardez le contrôle de vos hypothèses; ImmoRadar les organise et explique les résultats importants.</p>",
        unsafe_allow_html=True,
    )
    steps = st.columns(3)
    steps_content = [
        ("01", "Saisissez vos hypothèses", "Prix, mise de fonds, financement, revenus et dépenses : les éléments essentiels de votre scénario."),
        ("02", "Laissez les calculs travailler", "Les formules financières reconnues transforment vos données en résultats mensuels et annuels."),
        ("03", "Interprétez avec confiance", "Chaque indicateur est accompagné d'une explication simple pour mieux orienter votre prochaine étape."),
    ]
    for column, (number, title, copy) in zip(steps, steps_content):
        with column:
            st.markdown(
                f"<article class='step-card'><span class='step-number'>{number}</span>"
                f"<h3>{title}</h3><p>{copy}</p></article>",
                unsafe_allow_html=True,
            )

    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    st.markdown(
        "<p class='eyebrow'>POURQUOI IMMORADAR</p>"
        "<h2>Une analyse qui vous aide à poser les bonnes questions.</h2>",
        unsafe_allow_html=True,
    )
    benefits = st.columns(3)
    benefit_content = [
        ("◈", "Financement clair", "Visualisez immédiatement le prêt, le paiement mensuel et la pression sur votre budget."),
        ("↗", "Rentabilité lisible", "Mesurez le flux de trésorerie, le rendement sur la mise et le taux de capitalisation."),
        ("✓", "Décision transparente", "Distinguez vos hypothèses, les calculs et les données de marché avant de vous engager."),
    ]
    for column, (icon, title, copy) in zip(benefits, benefit_content):
        with column:
            st.markdown(
                f"<article class='benefit-card'><div class='feature-icon'>{icon}</div>"
                f"<h3>{title}</h3><p>{copy}</p></article>",
                unsafe_allow_html=True,
            )

    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown(
            "<p class='eyebrow'>TRANSPARENCE DES DONNÉES</p>"
            "<h2>Ce que vous voyez, clairement identifié.</h2>"
            "<p class='section-intro'>Vos chiffres de projet sont vos propres hypothèses. "
            "Les formules financières sont calculées dans l'application et restent distinctes des données de marché.</p>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            "<div class='data-card'><div><span class='data-pill real'>Donnée réelle</span>"
            "<h3>Taux directeur</h3><p>Banque du Canada, lorsqu'il est accessible.</p></div>"
            "<div><span class='data-pill simulated'>Données simulées</span>"
            "<h3>Repères de marché</h3><p>Inflation, chômage, prix, variations et historiques par ville.</p></div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div class='final-cta'><p class='hero-eyebrow'>PRÊT À COMMENCER</p>"
        "<h2>Évaluez votre prochaine propriété avec plus de confiance.</h2>"
        "<p>Commencez par vos propres chiffres : ImmoRadar s'occupe de les rendre exploitables.</p></div>",
        unsafe_allow_html=True,
    )
    final_col, _ = st.columns([1.25, 3.75])
    final_col.button(
        "Ouvrir l'analyse immobilière",
        type="primary",
        on_click=go_to,
        args=("Analyse immobilière",),
        use_container_width=True,
    )
