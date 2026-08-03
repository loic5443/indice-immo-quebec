"""Premium proposition centred on complete dossiers and future intelligent alerts."""

import streamlit as st

from components.account import current_user, is_authenticated
from data.database import DATABASE_PATH
from repositories.sqlite_repository import SQLiteRepository


def _feature(title: str, free: str, premium: str) -> None:
    left, right = st.columns(2)
    left.markdown(f"<div class='comparison-row'><b>{title}</b><span>{free}</span></div>", unsafe_allow_html=True)
    right.markdown(f"<div class='comparison-row premium-row'><b>{title}</b><span>{premium}</span></div>", unsafe_allow_html=True)


def show_premium() -> None:
    st.markdown("<section class='hero-image-panel'><div class='hero-content'><p class='hero-eyebrow notranslate'>IMMORADAR PREMIUM</p><h1>Révélez davantage. Suivez ce qui évolue.</h1><p class='hero-copy'>Premium approfondira vos dossiers immobiliers avec des analyses sans limite, des comparaisons, des rapports et des alertes intelligentes.</p></div></section>", unsafe_allow_html=True)
    st.info("Premium est actuellement en préparation. Aucun paiement n’est demandé pendant la bêta privée.")
    free, premium = st.columns(2)
    with free:
        st.markdown("<article class='plan-card'><p class='plan-label'>GRATUIT</p><h2>Découvrir un dossier</h2><p class='plan-price'>0 $ <span>pendant la bêta</span></p><p><b>Une révélation / estimation complète par mois</b>, lorsqu’elle est calculable.</p><p>Analyse financière, dossier de base et sauvegarde selon les droits actuels.</p><span class='data-pill real'>Disponible</span></article>", unsafe_allow_html=True)
    with premium:
        st.markdown("<article class='plan-card premium-card'><p class='plan-label accent-label'>PREMIUM</p><h2>Suivre chaque décision</h2><p class='plan-price'>Tarif à confirmer</p><p><b>Estimations illimitées</b>, dossiers, historique et explications détaillées.</p><p>Comparaisons, scénarios, PDF et alertes intelligentes.</p><span class='data-pill simulated'>Bientôt disponible</span></article>", unsafe_allow_html=True)
    st.markdown("<div class='section-space compact-space'></div><h2>Comparaison claire</h2>", unsafe_allow_html=True)
    free_header, premium_header = st.columns(2)
    free_header.caption("Gratuit")
    premium_header.caption("Premium")
    for values in (
        ("Estimations ImmoValue", "1 complète / mois lorsque calculable", "Illimitées"),
        ("Dossiers et historique", "Dossier de base", "Historique complet"),
        ("Explications et scénarios", "Calculs essentiels", "Détails et scénarios avancés"),
        ("Rapport PDF", "Disponible selon le dossier", "Rapport complet"),
        ("Comparaisons", "Aperçu", "Comparaisons avancées · bientôt disponible"),
        ("Alertes et suivi", "Aperçu verrouillé", "Alertes intelligentes · bientôt disponible"),
        ("Villes et données enrichies", "Repères officiels", "Bientôt disponible"),
    ):
        _feature(*values)
    st.markdown("<div class='premium-notice'><h3>Les alertes restent au cœur de Premium</h3><p>Une alerte est montrée seulement lorsqu’un changement vérifiable peut être calculé. Les autres fonctions de suivi sont affichées comme aperçus ou « bientôt disponible », jamais comme des événements réels.</p></div>", unsafe_allow_html=True)
    st.subheader("M’avertir au lancement")
    if not is_authenticated():
        st.info("Connectez-vous pour gérer localement votre intérêt pour Premium.")
        return
    user = current_user()
    with SQLiteRepository(DATABASE_PATH)._connect() as connection:
        interest = connection.execute("SELECT 1 FROM premium_interest WHERE user_id=?", (user["id"],)).fetchone()
    consent = st.checkbox("Je souhaite être avisé localement du lancement Premium", value=bool(interest))
    if st.button("M’avertir au lancement", type="primary"):
        with SQLiteRepository(DATABASE_PATH)._connect() as connection, connection:
            if consent:
                connection.execute("INSERT INTO premium_interest(user_id,consent) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET consent=1", (user["id"],))
                st.success("Votre intérêt est enregistré localement. Aucun service externe n’est contacté.")
            else:
                connection.execute("DELETE FROM premium_interest WHERE user_id=?", (user["id"],))
                st.info("Vous avez été retiré de la liste locale.")
