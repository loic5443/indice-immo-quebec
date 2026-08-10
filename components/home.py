"""Focused landing page: reveal a property, then monitor what can change."""

import base64
from pathlib import Path

import streamlit as st

from components.sidebar import go_to


IMAGE = Path(__file__).resolve().parents[1] / "assets" / "images" / "immoradar-hero.png"


@st.cache_data(show_spinner=False)
def _hero() -> str:
    if not IMAGE.exists():
        return ""
    encoded = base64.b64encode(IMAGE.read_bytes()).decode()
    return f"background-image:linear-gradient(95deg,rgba(7,23,45,.96),rgba(7,23,45,.60)),url('data:image/png;base64,{encoded}');"


def _start_from_home() -> None:
    # The landing page intentionally does not collect an address. Consent and
    # public-address lookups belong exclusively to the Analyse form.
    st.session_state["address_form_start_empty"] = True
    st.session_state.pop("home_address_pending", None)
    go_to("Analyser")


def show_home() -> None:
    st.markdown(
        f"<section class='hero-image-panel' style=\"{_hero()}\"><div class='hero-content'>"
        "<p class='hero-eyebrow notranslate'>IMMORADAR</p>"
        "<div class='hero-title' role='heading' aria-level='1'>Découvrez ce qu’une propriété pourrait valoir.</div>"
        "<p class='hero-copy'>Surveillez ensuite tout ce qui peut changer votre décision. ImmoRadar rassemble les renseignements disponibles, vos hypothèses et une lecture claire de votre dossier.</p>"
        "<p class='hero-proof'><span>Valeur expliquée</span><span>Hypothèses transparentes</span><span>Suivi utile</span></p>"
        "</div></section>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        spacer, action, premium, tail = st.columns([1.1, 1.35, 1.2, 1.1])
        with action:
            st.write("")
            st.button("Révéler la valeur", type="primary", on_click=_start_from_home, use_container_width=True)
        with premium:
            st.write("")
            st.button("Découvrir Premium", on_click=go_to, args=("Premium",), use_container_width=True)

    st.markdown("<div class='section-space'></div><p class='eyebrow'>UN SEUL DOSSIER</p><h2>De l’adresse à une décision plus lisible.</h2>", unsafe_allow_html=True)
    for column, number, title, copy in zip(
        st.columns(3),
        ("01", "02", "03"),
        ("Ajoutez l’adresse", "Révélez la valeur et analysez", "Suivez ce qui évolue"),
        (
            "Choisissez la recherche publique avec consentement, ou saisissez vos informations manuellement.",
            "Consultez le rôle municipal, ImmoValue seulement lorsque calculable, puis vos finances et votre score.",
            "Sauvegardez le dossier et activez les alertes disponibles ou les aperçus Premium verrouillés.",
        ),
    ):
        with column:
            st.markdown(f"<article class='step-card'><span class='step-number'>{number}</span><h3>{title}</h3><p>{copy}</p></article>", unsafe_allow_html=True)

    st.markdown("<div class='section-space'></div><p class='eyebrow'>APERÇU</p><h2>Une lecture qui va droit au point.</h2>", unsafe_allow_html=True)
    overview, notes = st.columns([1.2, 1])
    with overview:
        st.markdown(
            "<article class='dossier-preview'><span class='data-pill simulated'>Exemple d’interface</span>"
            "<h3>Dossier immobilier 360</h3><div class='preview-grid'><div><small>Valeur ImmoValue</small><strong>Calculable selon les comparables</strong></div>"
            "<div><small>Score ImmoRadar</small><strong>Lecture adaptée au projet</strong></div>"
            "<div><small>Confiance</small><strong>Qualité des données saisies</strong></div></div></article>",
            unsafe_allow_html=True,
        )
    with notes:
        st.markdown("<article class='benefit-card'><h3>Ce que vous voyez</h3><p>• La valeur municipale reste distincte d’une valeur marchande.</p><p>• Les points forts et les vérifications viennent des données réellement disponibles.</p><p>• Aucun résultat d’exemple n’est présenté comme le vôtre.</p></article>", unsafe_allow_html=True)

    st.markdown("<div class='section-space'></div><section class='premium-notice'><p class='eyebrow notranslate'>ALERTES PREMIUM</p><h2>Gardez une longueur d’avance</h2><p>Suivez les changements qui peuvent influencer vos décisions grâce aux alertes personnalisées ImmoRadar.</p><p><b>Aperçus verrouillés :</b> variation de valeur quand deux estimations fiables existent · impact d’un taux directeur sur un scénario · mise à jour du rôle municipal.</p><p>Les alertes non calculables restent indiquées « bientôt disponible ». Aucun courriel n’est envoyé pendant la bêta.</p></section>", unsafe_allow_html=True)
    st.button("Voir les alertes Premium", on_click=go_to, args=("Premium",), key="home_premium")

    st.markdown("<div class='section-space'></div><h2>Pourquoi ImmoRadar</h2>", unsafe_allow_html=True)
    for column, title, copy in zip(
        st.columns(4),
        ("Valeur", "Analyse", "Transparence", "Suivi"),
        ("Une estimation seulement lorsqu’elle est calculable.", "Des chiffres financiers et un score expliqués.", "Source, année et limites restent visibles.", "Vos dossiers et alertes utiles au même endroit."),
    ):
        with column:
            st.markdown(f"<article class='benefit-card'><h3>{title}</h3><p>{copy}</p></article>", unsafe_allow_html=True)
    st.markdown("<div class='final-cta'><h2>Prêt à ouvrir votre dossier immobilier?</h2><p>Commencez avec une adresse ou les hypothèses que vous avez déjà.</p></div>", unsafe_allow_html=True)
    st.button("Analyser une propriété", type="primary", on_click=_start_from_home, key="home_final_analysis")
