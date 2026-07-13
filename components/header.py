import streamlit as st


def show_header():
    """Render the ImmoRadar home-page introduction."""
    st.title("🏠 ImmoRadar")
    st.caption("Un outil d'aide à la décision immobilière pour le Québec et le Canada")
    st.markdown(
        """
        **Comprenez votre projet immobilier en quelques minutes.** ImmoRadar combine
        les indicateurs économiques, votre budget et le type de propriété afin de
        produire un score de contexte simple à lire. Il sert à préparer vos
        comparaisons et vos discussions avec des professionnels — pas à remplacer
        un conseil financier ou hypothécaire.
        """
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("1. Paramétrez", "Votre projet")
    col2.metric("2. Analysez", "Score sur 100")
    col3.metric("3. Comparez", "Vos scénarios")

    st.info(
        "Transparence des données : le taux directeur du Canada est récupéré "
        "automatiquement lorsque disponible. Les prix par ville, leur historique, "
        "l'inflation, le chômage et les prévisions affichés ici sont des données "
        "d'exemple à remplacer par des sources vérifiées."
    )
