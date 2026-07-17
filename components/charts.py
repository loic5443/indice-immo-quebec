import pandas as pd
import plotly.express as px
import streamlit as st

from data.market_data import market_stats


def show_market_chart(selected_city):
    st.subheader("Tendances immobilières")
    st.caption("Données simulées : elles ne constituent pas des statistiques de marché en temps réel.")

    if selected_city in market_stats:
        info = market_stats[selected_city]
        st.info(f"{selected_city} — Prix moyen indicatif : {info['prix']:,} $ | Variation : +{info['variation']} %")
    else:
        st.caption("La ville saisie ne fait pas partie du jeu de données d'exemple ci-dessous.")

    cols = st.columns(len(market_stats))
    for col, (ville, info) in zip(cols, market_stats.items()):
        col.metric(ville, f"{info['prix']:,} $", f"+{info['variation']} %")

    historique = pd.DataFrame({"Mois": ["Jan", "Fév", "Mars", "Avr", "Mai", "Juin"]})
    for ville, info in market_stats.items():
        historique[ville] = info["historique"]

    fig = px.line(historique, x="Mois", y=list(market_stats), markers=True, title="Évolution indicative des prix")
    fig.update_layout(paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font_color="#172033", title_font_size=20, legend_title_text="Ville")
    st.plotly_chart(fig, width="stretch", key="main_market_chart")
