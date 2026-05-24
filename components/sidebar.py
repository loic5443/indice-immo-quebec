import streamlit as st


def show_sidebar():

    st.sidebar.header("⚙️ Paramètres")

    market = st.sidebar.selectbox(
        "Marché",
        ["Québec / Canada", "États-Unis"]
    )

    mode = st.sidebar.radio(
        "Mode",
        ["Données automatiques", "Simulation personnalisée"]
    )

    ville = st.sidebar.text_input(
        "Ville",
        "Montréal"
    )

    type_propriete = st.sidebar.selectbox(
        "Type de propriété",
        ["Maison", "Condo", "Duplex", "Triplex", "Immeuble locatif"]
    )

    prix = st.sidebar.number_input(
        "Prix propriété ($)",
        value=450000,
        step=10000
    )

    mise = st.sidebar.number_input(
        "Mise de fonds ($)",
        value=50000,
        step=5000
    )

    revenu = st.sidebar.number_input(
        "Revenu annuel ($)",
        value=85000,
        step=5000
    )

    return (
        market,
        mode,
        ville,
        type_propriete,
        prix,
        mise,
        revenu
    )