"""Premium page focused on the concrete value of following a real dossier."""

import streamlit as st

from components.account import current_user, is_authenticated
from components.sidebar import go_to
from data.database import DATABASE_PATH
from services.entitlements_service import can_use
from services.premium_interest_service import has_premium_interest, set_premium_interest


def _feature(title: str, free: str, premium: str) -> None:
    free_column, premium_column = st.columns(2)
    free_column.markdown(
        f"<div class='comparison-row'><b>{title}</b><span>{free}</span></div>", unsafe_allow_html=True,
    )
    premium_column.markdown(
        f"<div class='comparison-row premium-row'><b>{title}</b><span>{premium}</span></div>", unsafe_allow_html=True,
    )


def _status(label: str, detail: str, state: str = "real") -> None:
    st.markdown(
        f"<div class='premium-capability'><span class='data-pill {state}'>{label}</span>"
        f"<p>{detail}</p></div>",
        unsafe_allow_html=True,
    )


def show_premium() -> None:
    st.markdown(
        "<section class='hero-image-panel premium-hero'><div class='hero-content'>"
        "<p class='hero-eyebrow notranslate'>IMMORADAR PREMIUM</p>"
        "<div class='hero-title' role='heading' aria-level='1'>Comprenez maintenant. Suivez ensuite ce qui change.</div>"
        "<p class='hero-copy'>Premium rassemble les dossiers, les scénarios et les changements vérifiables "
        "pour vous aider à revenir à une décision avec le bon contexte.</p>"
        "<p class='hero-proof'><span>Dossiers sans limite</span><span>Comparaisons claires</span>"
        "<span>Suivi utile</span></p></div></section>",
        unsafe_allow_html=True,
    )
    st.info("Premium est en préparation commerciale. Aucun paiement n’est demandé pendant la bêta privée.")

    if is_authenticated():
        user = current_user()
        if can_use(user, "alerts"):
            st.success("Votre accès Premium bêta est actif : vous pouvez déjà essayer les dossiers, comparaisons, rapports et suivi disponibles.")

    st.markdown(
        "<div class='section-space compact-space'></div><p class='eyebrow'>POURQUOI PASSER À PREMIUM</p>"
        "<div class='section-title' role='heading' aria-level='2'>Le dossier ne s’arrête pas au premier calcul.</div>"
        "<p class='section-intro'>Le gratuit vous aide à comprendre une propriété. Premium vous aide à conserver le fil "
        "quand vos hypothèses, vos comparables ou les données publiques évoluent.</p>",
        unsafe_allow_html=True,
    )
    for column, title, copy in zip(
        st.columns(3),
        ("Conserver le contexte", "Comparer sans repartir de zéro", "Surveiller l’important"),
        (
            "Gardez les instantanés, les hypothèses et les explications de vos dossiers au même endroit.",
            "Mettez deux dossiers sauvegardés côte à côte à partir de leurs valeurs déjà enregistrées.",
            "Voyez uniquement les changements calculables : rôle municipal, estimation, sensibilité au taux ou renouvellement saisi.",
        ),
    ):
        with column:
            st.markdown(f"<article class='benefit-card premium-benefit'><div class='card-title' role='heading' aria-level='3'>{title}</div><p>{copy}</p></article>", unsafe_allow_html=True)

    st.markdown("<div class='section-space compact-space'></div><div class='section-title' role='heading' aria-level='2'>Choisissez le niveau de suivi qui vous convient.</div>", unsafe_allow_html=True)
    free, premium = st.columns(2)
    with free:
        st.markdown(
            "<article class='plan-card'><p class='plan-label'>GRATUIT</p><div class='plan-title' role='heading' aria-level='3'>Découvrir une propriété</div>"
            "<p class='plan-price'>0 $ <span>pendant la bêta</span></p>"
            "<p><b>Une estimation ImmoValue complète par mois</b>, seulement lorsqu’elle est calculable.</p>"
            "<p>Vous conservez l’analyse financière de base et pouvez ouvrir un dossier clair avant de décider de la suite.</p>"
            "<p class='plan-feature'>✓ <span>Valeur municipale lorsqu’elle est disponible</span></p>"
            "<p class='plan-feature'>✓ <span>Finances et ImmoScore selon vos chiffres</span></p>"
            "<p class='plan-feature'>✓ <span>Aperçu de comparaison et de suivi</span></p>"
            "<span class='data-pill real'>Disponible</span></article>",
            unsafe_allow_html=True,
        )
        st.button("Commencer une analyse", type="primary", on_click=go_to, args=("Analyser",), key="premium_start_analysis", use_container_width=True)
    with premium:
        st.markdown(
            "<article class='plan-card premium-card'><p class='plan-label accent-label'>PREMIUM</p><div class='plan-title' role='heading' aria-level='3'>Suivre vos décisions</div>"
            "<p class='plan-price'>Tarif à confirmer</p>"
            "<p><b>Des estimations sans limite</b>, des dossiers complets et les outils utiles quand une décision mérite d’être suivie.</p>"
            "<p class='plan-feature'>✓ <span>Historique, comparaisons et scénarios détaillés</span></p>"
            "<p class='plan-feature'>✓ <span>Rapports PDF complets et dossiers suivis</span></p>"
            "<p class='plan-feature'>✓ <span>Alertes fondées sur des changements vérifiables</span></p>"
            "<span class='data-pill simulated'>Accès bêta technique</span></article>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<a class='premium-cta-link' href='#m-avertir-au-lancement'>M’avertir au lancement</a>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>CE QUI EST DÉJÀ CONCRET</p><div class='section-title' role='heading' aria-level='2'>Des outils utiles, sans promesse floue.</div>", unsafe_allow_html=True)
    current, future = st.columns(2)
    with current:
        st.markdown("<div class='subsection-title' role='heading' aria-level='3'>Disponible avec l’accès Premium bêta</div>", unsafe_allow_html=True)
        _status("Disponible", "Estimations ImmoValue illimitées lorsque trois comparables admissibles sont fournis.")
        _status("Disponible", "Comparaison de dossiers sauvegardés, scénarios et rapport PDF complet.")
        _status("Disponible", "Suivi local de changements réellement calculables. Aucun courriel n’est envoyé pendant la bêta.")
    with future:
        st.markdown("<div class='subsection-title' role='heading' aria-level='3'>En préparation</div>", unsafe_allow_html=True)
        _status("Bientôt disponible", "Alertes de suivi actives par courriel ou autre canal, seulement avec votre consentement.", "simulated")
        _status("Bientôt disponible", "Données enrichies et radar des occasions, après validation de chaque source.", "simulated")
        _status("Bientôt disponible", "Comparaisons municipales plus larges lorsque des données officielles comparables sont disponibles.", "simulated")

    st.markdown("<div class='section-space compact-space'></div><div class='section-title' role='heading' aria-level='2'>Ce qui se débloque réellement.</div>", unsafe_allow_html=True)
    free_header, premium_header = st.columns(2)
    free_header.caption("Gratuit")
    premium_header.caption("Premium")
    for values in (
        ("Estimations ImmoValue", "1 complète / mois lorsque calculable", "Illimitées lorsque calculables"),
        ("Dossiers", "Repères essentiels", "Historique et instantanés complets"),
        ("Comparaison", "Aperçu utile", "Lecture détaillée de deux dossiers"),
        ("Scénarios et rapport", "Calculs essentiels", "Scénarios sauvegardés et PDF complet"),
        ("Suivi", "Aperçu verrouillé", "Changements vérifiables dans vos dossiers suivis"),
    ):
        _feature(*values)

    st.markdown(
        "<div class='premium-notice'><div class='notice-title' role='heading' aria-level='3'>Une alerte n’est jamais inventée.</div>"
        "<p>ImmoRadar montre une alerte seulement lorsqu’un changement peut être établi avec les instantanés "
        "sauvegardés ou une source autorisée. Une valeur municipale demeure un repère fiscal, pas une valeur marchande.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div id='m-avertir-au-lancement' class='section-space compact-space'></div><div class='section-title' role='heading' aria-level='2'>M’avertir au lancement</div>", unsafe_allow_html=True)
    st.caption("Votre intérêt reste enregistré uniquement dans ImmoRadar. Aucun service externe n’est contacté.")
    if not is_authenticated():
        st.info("Connectez-vous pour gérer localement votre intérêt pour Premium.")
        st.button("Créer mon espace pour être averti", type="primary", on_click=go_to, args=("Mon compte",), key="premium_open_account")
        return

    user = current_user()
    interest = has_premium_interest(user["id"], DATABASE_PATH)
    if interest:
        st.success("Votre intérêt pour Premium est enregistré localement. Aucun avis externe n’est envoyé pendant la bêta.")
    consent = st.checkbox(
        "Je souhaite être avisé localement du lancement Premium",
        value=interest,
        key="premium_interest_consent",
    )
    if st.button("Enregistrer mon choix", type="primary", key="premium_interest_save"):
        set_premium_interest(user["id"], consent, DATABASE_PATH)
        if consent:
            st.success("Votre intérêt est enregistré localement. Aucun service externe n’est contacté.")
        else:
            st.info("Vous avez été retiré de la liste locale.")
