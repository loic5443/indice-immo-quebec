import streamlit as st


def show_header():
    """Render the ImmoRadar home-page introduction."""
    st.title("🏠 ImmoRadar")
    st.caption("Un outil d'aide à la décision immobilière pour le Québec et le Canada")
    st.markdown(
        """
        **Comprenez votre projet immobilier en quelques minutes.** ImmoRadar combine
        les indicateurs économiques, votre budget et le type de propriété afin de
        produire une analyse de projet claire. La fiche d'analyse calcule votre
        financement, vos dépenses, votre flux de trésorerie et vos principaux ratios.
        Elle aide à préparer vos comparaisons, sans remplacer un conseil financier.
        """
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("1. Saisissez", "Votre projet")
    col2.metric("2. Analysez", "Vos chiffres")
    col3.metric("3. Comparez", "Vos scénarios")

    st.info(
        "Transparence des données : le taux directeur du Canada est récupéré "
        "automatiquement lorsque disponible. Les prix par ville, leur historique, "
        "l'inflation et le chômage affichés ici sont des données simulées."
    )
