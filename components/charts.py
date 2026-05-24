import streamlit as st
import pandas as pd
import plotly.express as px

from data.market_data import market_stats


def show_market_chart(selected_city):

    st.header("📈 Tendances immobilières")

    if selected_city in market_stats:

        infos = market_stats[selected_city]

        st.success(
            f"📍 {selected_city} — Prix moyen : {infos['prix']} | Variation : {infos['variation']}"
        )

    cols = st.columns(4)

    for col, (ville, infos) in zip(cols, market_stats.items()):

        col.metric(
            f"🏙️ {ville}",
            infos["prix"],
            infos["variation"]
        )

    historique = pd.DataFrame({
        "Mois": ["Jan", "Fév", "Mars", "Avr", "Mai", "Juin"],
        "Montréal": [100, 104, 108, 112, 118, 121],
        "Québec": [100, 101, 103, 105, 107, 110],
        "Laval": [100, 102, 106, 107, 109, 113],
        "Gatineau": [100, 103, 105, 108, 111, 115]
    })

    fig2 = px.line(
        historique,
        x="Mois",
        y=["Montréal", "Québec", "Laval", "Gatineau"],
        markers=True,
        title="Évolution des prix immobiliers"
    )

    fig2.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        title_font_size=24
    )

    st.plotly_chart(
        fig2,
        use_container_width=True,
        key="main_market_chart"
    )