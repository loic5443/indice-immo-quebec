"""Market page with explicitly labelled local examples and live macro context."""

import streamlit as st

from components.charts import show_city_comparison_chart, show_market_overview_charts
from data.real_data import get_canada_policy_rate
from data.simulated_data import SIMULATED_INFLATION, SIMULATED_MARKET_STATS, SIMULATED_UNEMPLOYMENT


def _market_card(city: str, data: dict[str, object]) -> None:
    """Render one city snapshot while making its illustrative status unambiguous."""
    st.markdown(
        f"""
        <article class="market-card">
          <div class="market-card-top"><h3>{city}</h3><span class="data-pill simulated">Données simulées</span></div>
          <strong class="market-price">{data['prix']:,} $</strong><span class="market-price-label">prix moyen indicatif</span>
          <div class="market-details">
            <span>Variation annuelle <b>+{data['variation']} %</b></span>
            <span>Rendement locatif <b>{data['rendement']} %</b></span>
            <span>Risque <b>{data['risque']}</b></span>
            <span>Tendance <b>{data['tendance']}</b></span>
          </div>
          <p>Mise à jour : {data['mise_a_jour']} · Exemple de présentation</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _comparison_metrics(city: str, data: dict[str, object]) -> None:
    """Display a compact, comparable city summary."""
    st.markdown(f"<p class='comparison-city'>{city}</p>", unsafe_allow_html=True)
    st.metric("Prix moyen indicatif", f"{data['prix']:,} $")
    st.metric("Variation annuelle", f"+{data['variation']} %")
    st.metric("Rendement locatif estimé", f"{data['rendement']} %")
    st.markdown(
        f"<p class='comparison-detail'><b>Risque :</b> {data['risque']}<br>"
        f"<b>Tendance :</b> {data['tendance']}<br>"
        f"<b>Mise à jour :</b> {data['mise_a_jour']}</p>",
        unsafe_allow_html=True,
    )


def show_markets() -> None:
    """Display market context, illustrative city cards, and a city comparison tool."""
    st.markdown(
        "<p class='eyebrow'>CONTEXTE DE MARCHÉ</p><h1>Comparez les repères avant d'approfondir un projet.</h1>"
        "<p class='section-intro'>ImmoRadar sépare les indicateurs externes disponibles des exemples locaux utilisés pour présenter le produit.</p>",
        unsafe_allow_html=True,
    )

    rate, is_live = get_canada_policy_rate()
    one, two, three = st.columns(3)
    one.metric("Taux directeur du Canada", f"{rate:.2f} %", "Donnée réelle" if is_live else "Valeur de repli")
    two.metric("Inflation", f"{SIMULATED_INFLATION:.1f} %", "Donnée simulée")
    three.metric("Chômage", f"{SIMULATED_UNEMPLOYMENT:.1f} %", "Donnée simulée")

    st.warning(
        "Les données par ville, les rendements, les niveaux de risque et les graphiques ci-dessous sont simulés. "
        "Ils servent à illustrer ImmoRadar et ne remplacent pas une étude de marché vérifiée."
    )

    st.markdown("<div class='section-space compact-space'></div><h2>Repères par ville</h2>", unsafe_allow_html=True)
    cities = list(SIMULATED_MARKET_STATS.items())
    for first_index in range(0, len(cities), 3):
        columns = st.columns(3)
        for column, (city, data) in zip(columns, cities[first_index:first_index + 3]):
            with column:
                _market_card(city, data)

    st.markdown("<div class='section-space'></div><p class='eyebrow'>VUE D'ENSEMBLE</p><h2>Des graphiques simples pour situer les écarts.</h2>", unsafe_allow_html=True)
    show_market_overview_charts()

    st.markdown("<div class='section-space'></div><p class='eyebrow'>COMPARATEUR DE VILLES</p><h2>Comparez deux scénarios de marché.</h2>", unsafe_allow_html=True)
    city_names = list(SIMULATED_MARKET_STATS)
    selector_one, selector_two = st.columns(2)
    with selector_one:
        first_city = st.selectbox("Première ville", city_names, key="market_first_city")
    with selector_two:
        alternative_cities = [city for city in city_names if city != first_city]
        second_city = st.selectbox("Deuxième ville", alternative_cities, index=0, key="market_second_city")

    comparison_one, comparison_two = st.columns(2)
    with comparison_one:
        _comparison_metrics(first_city, SIMULATED_MARKET_STATS[first_city])
    with comparison_two:
        _comparison_metrics(second_city, SIMULATED_MARKET_STATS[second_city])
    st.caption("Comparaison fondée sur des données simulées et des historiques indicatifs.")
    show_city_comparison_chart(first_city, second_city)
