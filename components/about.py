"""About page for product positioning and data transparency."""

import streamlit as st


def show_about() -> None:
    st.title("À propos d’ImmoRadar")
    st.write("ImmoRadar est un outil d’aide à la décision conçu pour rendre l’analyse immobilière plus claire avant une offre, une négociation ou une discussion avec un professionnel.")
    first, second = st.columns(2)
    with first:
        with st.container(border=True):
            st.subheader("Notre approche")
            st.write("Nous séparons vos hypothèses, les calculs et les repères de marché afin que chaque résultat reste compréhensible.")
    with second:
        with st.container(border=True):
            st.subheader("Ce qu’ImmoRadar ne fait pas")
            st.write("Il ne remplace pas un courtier, un fiscaliste, un conseiller financier ou une évaluation professionnelle.")
    st.subheader("Données et limites")
    st.write("Le taux directeur canadien provient de la Banque du Canada lorsqu'une valeur officielle est disponible. Les prix, rendements et comparaisons de villes ne sont pas affichés tant qu'une source, une licence et une méthode ne sont pas validées. Les données de démonstration ne font pas partie de l'expérience publique.")
