"""Public market context: official observations only, with transparent degraded states."""

import streamlit as st

from data.database import DATABASE_PATH
from providers.official_data import BankOfCanadaPolicyRateProvider
from providers.source_registry import integrated_sources
from services.market_data_service import cached_policy_rate, refresh_source


def _source_card(source: dict[str, object]) -> None:
    st.markdown(f"**{source['name']}** · Donnée observée officielle")
    st.caption(f"Actualisation prévue : {source['refresh_frequency']} · {source['license_summary']}")
    st.link_button("Ouvrir la source officielle", str(source["human_url"]), use_container_width=False)


def _unavailable(title: str, detail: str) -> None:
    st.markdown(f"<div class='market-card'><h3>{title}</h3><strong>Donnée indisponible</strong><p>{detail}</p></div>", unsafe_allow_html=True)


def show_markets() -> None:
    """Show only officially integrated observations; never substitute illustrative city data."""
    st.markdown("<p class='eyebrow'>DONNÉES DE MARCHÉ</p><h1>Des repères officiels, jamais des chiffres inventés.</h1>"
                "<p class='section-intro'>Chaque indicateur public affiche sa source, sa date et son statut. Les indicateurs québécois par ville restent indisponibles tant que leur source et leur méthode ne sont pas validées.</p>", unsafe_allow_html=True)
    with st.spinner("Vérification de la source officielle disponible..."):
        refresh_source(str(DATABASE_PATH), BankOfCanadaPolicyRateProvider())
    rate = cached_policy_rate(str(DATABASE_PATH))
    left, right = st.columns((1, 1))
    with left:
        if rate:
            freshness = "à jour" if rate["freshness"] == "fresh" else "dernière valeur valide — à rafraîchir"
            st.metric("Taux directeur du Canada", f"{rate['value']:.2f} %", freshness)
            st.caption(f"Observé le {rate['observed_at']} · récupéré le {rate['retrieved_at']} · donnée observée officielle.")
            st.link_button("Consulter la donnée source", rate["source_url"])
        else:
            _unavailable("Taux directeur du Canada", "La source officielle est momentanément inaccessible et aucune valeur valide n'est encore en cache local.")
    with right:
        _unavailable("Marchés québécois par ville", "Prix, variation, rendement et risque ne sont pas publiés ici sans source officiellement validée. Aucune donnée simulée n'est affichée.")
    st.markdown("<div class='section-space'></div><h2>Comparaison de villes</h2>", unsafe_allow_html=True)
    st.info("Indisponible pour le moment : ImmoRadar n'effectue aucune comparaison de villes tant que les séries officielles, leur licence et leur couverture géographique ne sont pas validées.")
    st.markdown("<div class='section-space'></div><h2>Sources et méthodologie</h2>", unsafe_allow_html=True)
    st.write("Les données observées sont séparées des hypothèses saisies, des calculs dérivés et des contenus de démonstration. Elles ne modifient ni le Score ImmoRadar ni son verdict.")
    for source in integrated_sources():
        _source_card(source)
    with st.expander("Pourquoi certains indicateurs ne sont-ils pas affichés ?"):
        st.write("Une absence de donnée est préférée à une approximation. La disponibilité dépend de la validation de la source, de la licence, du territoire, de la fréquence et des contrôles de qualité.")
