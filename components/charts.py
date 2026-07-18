"""Charts used by the market experience."""

import pandas as pd
import plotly.express as px
import streamlit as st

from data.market_data import market_stats


def _apply_market_theme(figure):
    """Keep market charts readable and visually consistent with ImmoRadar."""
    figure.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font_color="#172033",
        margin=dict(l=10, r=10, t=55, b=10),
        legend_title_text="Ville",
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#edf1f6")
    return figure


def show_market_overview_charts() -> None:
    """Show simple overview charts for the illustrative city dataset."""
    chart_data = pd.DataFrame.from_dict(market_stats, orient="index").reset_index()
    chart_data = chart_data.rename(columns={"index": "Ville", "prix": "Prix moyen", "rendement": "Rendement locatif"})

    left, right = st.columns(2)
    with left:
        figure = px.bar(
            chart_data,
            x="Ville",
            y="Prix moyen",
            color="Ville",
            title="Prix moyen indicatif par ville",
            labels={"Prix moyen": "Prix moyen ($)"},
        )
        figure.update_layout(showlegend=False)
        st.plotly_chart(_apply_market_theme(figure), width="stretch", key="market_price_chart")
    with right:
        figure = px.bar(
            chart_data,
            x="Ville",
            y="Rendement locatif",
            color="Ville",
            title="Rendement locatif estimé",
            labels={"Rendement locatif": "Rendement (%)"},
        )
        figure.update_layout(showlegend=False)
        st.plotly_chart(_apply_market_theme(figure), width="stretch", key="market_yield_chart")


def show_city_comparison_chart(first_city: str, second_city: str) -> None:
    """Plot the simulated historical price paths for two selected cities."""
    history = pd.DataFrame(
        {
            "Mois": ["Jan", "Fév", "Mars", "Avr", "Mai", "Juin"],
            first_city: market_stats[first_city]["historique"],
            second_city: market_stats[second_city]["historique"],
        }
    )
    figure = px.line(
        history,
        x="Mois",
        y=[first_city, second_city],
        markers=True,
        title="Évolution indicative des prix",
        labels={"value": "Prix moyen ($)", "variable": "Ville"},
    )
    st.plotly_chart(_apply_market_theme(figure), width="stretch", key="selected_city_comparison")
