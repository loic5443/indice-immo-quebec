import streamlit as st


def show_sidebar():
    """Return the navigation and analysis inputs selected by the visitor."""
    st.sidebar.title("ImmoRadar")
    page = st.sidebar.radio("Navigation", ["Accueil", "Premium"], label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.header("Paramètres du projet")

    market = st.sidebar.selectbox("Marché", ["Québec / Canada", "États-Unis"])
    mode = st.sidebar.radio("Mode", ["Données automatiques", "Simulation personnalisée"])
    ville = st.sidebar.text_input("Ville", "Montréal")
    type_propriete = st.sidebar.selectbox(
        "Type de propriété", ["Maison", "Condo", "Duplex", "Triplex", "Immeuble locatif"]
    )
    prix = st.sidebar.number_input("Prix de la propriété ($)", min_value=1_000, value=450_000, step=10_000)
    mise = st.sidebar.number_input("Mise de fonds ($)", min_value=0, value=50_000, step=5_000)
    revenu = st.sidebar.number_input("Revenu annuel ($)", min_value=1_000, value=85_000, step=5_000)

    st.sidebar.caption("Aucun paiement ni abonnement réel n'est activé dans cette version.")
    return page, market, mode, ville, type_propriete, prix, mise, revenu
