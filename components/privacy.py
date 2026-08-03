"""Short, product-facing privacy notice kept outside the primary navigation."""

import streamlit as st


def show_privacy() -> None:
    st.markdown("<p class='eyebrow'>CONFIDENTIALITÉ</p><h1>Vos renseignements restent sous votre contrôle.</h1>", unsafe_allow_html=True)
    st.write("ImmoRadar conserve localement les données nécessaires à votre compte, vos brouillons et vos dossiers sauvegardés. Les calculs utilisent vos hypothèses; ils ne sont pas transmis à une source externe.")
    st.subheader("Recherche d’adresse publique")
    st.write("Une recherche auprès de la source officielle MRNF est effectuée seulement après votre consentement. La requête, les suggestions et les coordonnées ne sont pas envoyées à la télémétrie ni aux diagnostics.")
    st.subheader("Mesures techniques")
    st.write("Les mesures analytiques sont facultatives et n’acceptent aucun renseignement financier, mot de passe, adresse, comparable ou contenu de rapport.")
    st.caption("Cette page résume le fonctionnement du produit pendant la bêta privée; elle ne remplace pas les procédures internes de sécurité.")
