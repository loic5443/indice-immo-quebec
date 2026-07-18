"""Premium product page. No payments or account actions are enabled."""

import pandas as pd
import streamlit as st


FREE_FEATURES = [
    "Analyse immobilière de base",
    "Calcul du paiement et des dépenses",
    "Flux de trésorerie mensuel",
    "Ratios de rendement essentiels",
    "Repères de marché identifiés",
]

PREMIUM_FEATURES = [
    "Analyses illimitées",
    "Rapports détaillés",
    "Historique des analyses",
    "Alertes de marché enrichies",
    "Comparaisons avancées",
    "Export PDF",
    "Données enrichies",
]


def _feature_list(items: list[str]) -> None:
    for item in items:
        st.markdown(f"<p class='plan-feature'>✓ <span>{item}</span></p>", unsafe_allow_html=True)


def show_premium() -> None:
    """Present the planned paid tier without initiating a commercial transaction."""
    st.markdown(
        "<p class='eyebrow'>IMMORADAR PREMIUM</p><h1>Des outils prévus pour aller plus loin.</h1>"
        "<p class='section-intro'>Comparez le plan gratuit à la feuille de route Premium. "
        "Les fonctions annoncées sont présentées de façon transparente avant leur activation.</p>",
        unsafe_allow_html=True,
    )
    st.warning("Aucun paiement réel, Stripe ni compte utilisateur n'est activé dans cette version.")

    free, premium = st.columns(2)
    with free:
        st.markdown("<section class='plan-card'><p class='plan-label'>GRATUIT</p><h2>Essentiel</h2><p class='plan-price'>0 $ <span>/ mois</span></p><p>Pour évaluer les fondamentaux d'un projet.</p>", unsafe_allow_html=True)
        _feature_list(FREE_FEATURES)
        st.button("Disponible maintenant", disabled=True, use_container_width=True, key="free_plan")
        st.markdown("</section>", unsafe_allow_html=True)
    with premium:
        st.markdown("<section class='plan-card premium-card'><p class='plan-label accent-label'>PREMIUM · BIENTÔT</p><h2>Investisseur</h2><p class='plan-price'>19 $ <span>/ mois · prix provisoire</span></p><p>Pour multiplier les scénarios et consolider votre recherche.</p>", unsafe_allow_html=True)
        _feature_list(PREMIUM_FEATURES)
        st.button("Premium bientôt disponible", disabled=True, use_container_width=True, key="premium_plan")
        st.markdown("</section>", unsafe_allow_html=True)

    st.markdown("<div class='section-space'></div><p class='eyebrow'>COMPARAISON DES FORFAITS</p><h2>Ce qui est prévu dans chaque expérience.</h2>", unsafe_allow_html=True)
    comparison = pd.DataFrame(
        [
            ("Analyse immobilière", "Inclus", "Inclus"),
            ("Analyses illimitées", "—", "Prévu"),
            ("Rapports détaillés", "—", "Prévu"),
            ("Historique des analyses", "—", "Prévu"),
            ("Alertes", "Aperçu", "Enrichies · prévu"),
            ("Comparaisons", "Villes", "Avancées · prévu"),
            ("Export PDF", "—", "Prévu"),
            ("Données enrichies", "—", "Prévu"),
        ],
        columns=["Fonctionnalité", "Gratuit", "Premium"],
    )
    st.dataframe(comparison, hide_index=True, width="stretch")
    st.caption("« Prévu » indique une fonctionnalité annoncée, mais non encore active dans cette version.")

    st.markdown("<div class='premium-notice'><h3>Activation responsable</h3><p>Premium sera activé seulement lorsque les données et les fonctionnalités annoncées seront prêtes. Aucun prélèvement ne peut être effectué aujourd'hui.</p></div>", unsafe_allow_html=True)
