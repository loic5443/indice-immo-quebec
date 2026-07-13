import streamlit as st


def show_sidebar():
    """Render simple product navigation without mixing it with financial inputs."""
    st.sidebar.title("ImmoRadar")
    page = st.sidebar.radio("Navigation", ["Accueil", "Analyse immobilière", "Premium"], label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Aucun paiement, abonnement ou compte utilisateur n'est activé.")
    return page
