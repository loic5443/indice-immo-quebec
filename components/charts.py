import streamlit as st
import pandas as pd
import plotly.express as px

from data.market_data import market_stats


def show_market_chart(selected_city):

    st.header("📈 Tendances immobilières")

    if selected_city in market_stats:

        infos_selected = market_stats[selected_city]

        st.success(
            f"📍 {selected_city} — Prix moyen : {infos_selected['prix']:,}$ | Variation : +{infos_selected['variation']}%"
        )

    cols = st.columns(len(market_stats))

    for col, (ville, infos) in zip(cols, market_stats.items()):

        col.metric(
            f"🏙️ {ville}",
            f"{infos['prix']:,}$",
            f"+{infos['variation']}%"
        )

    historique = pd.DataFrame({
        "Mois": ["Jan", "Fév", "Mars", "Avr", "Mai", "Juin"]
    })

    for ville, infos in market_stats.items():

        historique[ville] = infos["historique"]

    fig2 = px.line(
        historique,
        x="Mois",
        y=list(market_stats.keys()),
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