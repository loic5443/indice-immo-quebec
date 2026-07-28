"""Charts for validated official market observations only."""

import pandas as pd
import plotly.express as px
import streamlit as st

from domain.market_data import MarketObservation


def show_market_overview_charts(observations: list[MarketObservation]) -> None:
    if not observations:
        st.info("Aucune série officielle comparable n'est disponible pour ce graphique.")
        return
    data = pd.DataFrame([item.to_snapshot() for item in observations])
    st.plotly_chart(px.line(data, x="observed_at", y="value", title="Série officielle observée"), width="stretch")


def show_city_comparison_chart(*_args: str) -> None:
    """Compatibility placeholder until an official city series is approved."""
    st.info("Comparaison indisponible sans séries officielles par ville.")
