"""Premium product page. No payments or account actions are enabled."""

import streamlit as st


def _feature_list(items: list[str]) -> None:
    for item in items:
        st.markdown(f"<p class='plan-feature'>✓ <span>{item}</span></p>", unsafe_allow_html=True)


def show_premium() -> None:
    st.markdown("<p class='eyebrow'>IMMORADAR PREMIUM</p><h1>Approfondissez vos décisions immobilières.</h1>", unsafe_allow_html=True)
    st.write("Premium est en préparation. Cette page présente les fonctionnalités prévues; aucun paiement ni abonnement ne peut être effectué aujourd’hui.")
    st.warning("Aucun paiement réel, Stripe ni compte utilisateur n'est activé dans cette version.")

    free, premium = st.columns(2)
    with free:
        with st.container(border=True):
            st.markdown("<p class='plan-label'>GRATUIT</p><h2>Essentiel</h2><p class='plan-price'>0 $ <span>/ mois</span></p>", unsafe_allow_html=True)
            st.write("Les éléments fondamentaux pour comprendre un projet.")
            _feature_list([
                "Analyse de financement",
                "Paiement hypothécaire et dépenses",
                "Flux de trésorerie mensuel",
                "Rendement, capitalisation et couverture de dette",
                "Repères de marché identifiés",
            ])
            st.button("Disponible maintenant", disabled=True, use_container_width=True, key="free_plan")
    with premium:
        with st.container(border=True):
            st.markdown("<p class='plan-label accent-label'>PREMIUM · BIENTÔT</p><h2>Investisseur</h2><p class='plan-price'>19 $ <span>/ mois · prix provisoire</span></p>", unsafe_allow_html=True)
            st.write("Des outils supplémentaires pour comparer et suivre vos scénarios.")
            _feature_list([
                "Comparaison de scénarios",
                "Rapports exportables",
                "Alertes de marché enrichies",
                "Suivi multi-propriétés",
                "Analyse de portefeuille",
            ])
            st.button("Premium bientôt disponible", disabled=True, use_container_width=True, key="premium_plan")

    st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
    st.subheader("Une évolution guidée par la clarté")
    st.write("Le plan Premium sera activé seulement lorsque les données et les fonctionnalités annoncées seront prêtes. Aucun prélèvement ne sera effectué avant une activation explicite.")
