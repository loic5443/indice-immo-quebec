"""Trust-focused explanation of ImmoRadar outside the main product flow."""

import streamlit as st

from components.sidebar import go_to


def _principle(title: str, copy: str, label: str) -> None:
    st.markdown(
        f"<article class='benefit-card'><p class='eyebrow'>{label}</p>"
        f"<div class='card-title' role='heading' aria-level='3'>{title}</div><p>{copy}</p></article>",
        unsafe_allow_html=True,
    )


def show_about() -> None:
    st.markdown("<p class='eyebrow notranslate'>À PROPOS D’IMMORADAR</p>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title' role='heading' aria-level='1'>Comprendre une propriété avant une grande décision.</div>"
        "<p class='section-intro'>ImmoRadar rassemble les renseignements publics autorisés, vos chiffres et des "
        "méthodes expliquées pour rendre un dossier immobilier plus lisible. Vous restez responsable des hypothèses "
        "et de la décision finale.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>UNE LECTURE TRANSPARENTE</p><div class='section-title' role='heading' aria-level='2'>Trois choses, clairement séparées.</div>", unsafe_allow_html=True)
    first, second, third = st.columns(3)
    with first:
        _principle("Valeur municipale officielle", "Lorsqu’un rôle municipal public est disponible, ImmoRadar affiche sa source, son année et sa date de référence. C’est un repère fiscal, pas une valeur marchande.", "OFFICIEL")
    with second:
        _principle("Votre analyse financière", "Les paiements, dépenses, flux de trésorerie et ratios sont calculés à partir des chiffres que vous saisissez. Chaque résultat conserve son explication.", "VOS HYPOTHÈSES")
    with third:
        _principle("ImmoValue expérimental", "Une fourchette est produite seulement avec au moins trois comparables admissibles que vous fournissez et confirmez. Sans comparables suffisants, aucune estimation n’est inventée.", "CONDITIONNEL")

    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>COMMENT ÇA VOUS AIDE</p><div class='section-title' role='heading' aria-level='2'>Préparez une décision plus claire.</div>", unsafe_allow_html=True)
    for column, title, copy in zip(
        st.columns(3),
        ("Rassemblez le dossier", "Comprenez l’essentiel", "Revenez au bon moment"),
        (
            "Partez d’une adresse, de renseignements publics disponibles ou de vos propres hypothèses.",
            "Voyez les valeurs séparées, les chiffres clés, les points forts et les éléments à vérifier avant les détails techniques.",
            "Sauvegardez vos dossiers. Premium ajoute les comparaisons, les scénarios, le rapport et le suivi des changements vérifiables.",
        ),
    ):
        with column:
            st.markdown(f"<article class='benefit-card'><div class='card-title' role='heading' aria-level='3'>{title}</div><p>{copy}</p></article>", unsafe_allow_html=True)

    st.markdown("<div class='section-space compact-space'></div><div class='premium-notice'><div class='notice-title' role='heading' aria-level='3'>Ce qu’ImmoRadar ne prétend pas faire.</div><p>ImmoRadar ne produit pas une évaluation officielle, ne remplace pas un courtier, un évaluateur, un prêteur ou un conseiller, et ne garantit jamais qu’une propriété constitue un bon achat. Une donnée absente reste indiquée comme indisponible.</p></div>", unsafe_allow_html=True)
    st.caption("Les recherches publiques ne sont effectuées qu’avec votre consentement. Les adresses, montants et comparables ne sont pas envoyés à la télémétrie.")

    st.markdown("<div class='section-space compact-space'></div><div class='section-title' role='heading' aria-level='2'>Prêt à ouvrir votre dossier?</div><p class='section-intro'>Commencez par la propriété et les chiffres que vous connaissez déjà. Les étapes suivantes restent visibles et explicables.</p>", unsafe_allow_html=True)
    analyse, premium, _ = st.columns([1, 1, 2])
    analyse.button("Analyser une propriété", type="primary", on_click=go_to, args=("Analyser",), use_container_width=True)
    premium.button("Découvrir Premium", on_click=go_to, args=("Premium",), use_container_width=True)
    st.caption("ImmoRadar — bêta privée. Aucun paiement réel n’est demandé pendant cette période.")
