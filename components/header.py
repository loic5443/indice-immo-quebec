import streamlit as st


def show_header():

    st.markdown("""
    # 🏠 ImmoRadar Québec

    ### L’indice immobilier intelligent du Québec et du Canada

    Analysez le marché immobilier grâce aux taux d’intérêt, à l’inflation, au chômage et aux tendances économiques.
    """)

    hero1, hero2, hero3 = st.columns(3)

    hero1.metric("📈 Marché Québec", "+4.2%")
    hero2.metric("🏠 Prix moyen", "612 000$")
    hero3.metric("🔥 Opportunité", "Montréal")

    st.divider()