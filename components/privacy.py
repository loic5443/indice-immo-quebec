"""Plain-language privacy information for the secondary product navigation."""

import streamlit as st

from components.sidebar import go_to


def _privacy_card(label: str, title: str, copy: str) -> None:
    st.markdown(
        f"<article class='benefit-card'><p class='eyebrow'>{label}</p>"
        f"<div class='card-title' role='heading' aria-level='3'>{title}</div>"
        f"<p>{copy}</p></article>",
        unsafe_allow_html=True,
    )


def show_privacy() -> None:
    """Explain the privacy choices that exist in the product without legal jargon."""
    st.markdown("<p class='eyebrow'>CONFIDENTIALITÉ</p>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title' role='heading' aria-level='1'>Vos données servent votre dossier — pas un profil public.</div>"
        "<p class='section-intro'>ImmoRadar conserve localement les renseignements nécessaires à votre compte, vos brouillons "
        "et vos dossiers sauvegardés. Vous choisissez quand une recherche publique peut être effectuée et vous gardez "
        "le contrôle de vos données.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>EN BREF</p><div class='section-title' role='heading' aria-level='2'>Trois règles simples.</div>", unsafe_allow_html=True)
    local, consent, telemetry = st.columns(3)
    with local:
        _privacy_card("LOCAL", "Vos dossiers restent dans votre espace", "Vos hypothèses, brouillons et analyses sauvegardées servent à afficher votre dossier et votre historique. Vos mots de passe ne sont jamais conservés en clair.")
    with consent:
        _privacy_card("VOTRE CHOIX", "Une adresse publique seulement avec accord", "La recherche d’adresse auprès de la source officielle MRNF est effectuée seulement après votre consentement. Vous pouvez toujours poursuivre votre analyse manuellement.")
    with telemetry:
        _privacy_card("MESURES LIMITÉES", "Aucune adresse dans les mesures", "Les mesures analytiques sont désactivées par défaut. Si vous les activez, elles n’acceptent ni adresse, ni montant, ni comparable, ni mot de passe, ni contenu de rapport.")

    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>CE QUI EST PARTAGÉ, ET CE QUI NE L’EST PAS</p><div class='section-title' role='heading' aria-level='2'>Une recherche publique reste ciblée.</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='data-card'>"
        "<div><span class='data-pill real'>AVEC VOTRE CONSENTEMENT</span><h3>Recherche d’adresse publique</h3><p>La requête sert uniquement à obtenir des suggestions ou des renseignements publics autorisés auprès de la source officielle indiquée dans le dossier.</p></div>"
        "<div><span class='data-pill simulated'>JAMAIS DANS LA TÉLÉMÉTRIE</span><h3>Adresse, montants et comparables</h3><p>Ces renseignements ne sont pas envoyés aux mesures, aux diagnostics ou aux journaux techniques.</p></div>"
        "<div><span class='data-pill simulated'>PAS DE PAIEMENT</span><h3>Aucun traitement de carte pendant la bêta</h3><p>Premium est en préparation. ImmoRadar ne demande aucun paiement réel pendant la bêta privée.</p></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>VOS CONTRÔLES</p><div class='section-title' role='heading' aria-level='2'>Consultez, exportez ou supprimez vos données.</div><p class='section-intro'>Dans Mon compte, vous pouvez modifier vos consentements, télécharger vos données ou supprimer votre compte. L’export inclut votre profil et vos analyses, jamais votre mot de passe.</p>", unsafe_allow_html=True)
    account, analysis, _ = st.columns([1, 1, 2])
    account.button("Gérer mes données", type="primary", on_click=go_to, args=("Mon compte",), use_container_width=True)
    analysis.button("Analyser une propriété", on_click=go_to, args=("Analyser",), use_container_width=True)

    st.caption("Cette page résume le fonctionnement du produit pendant la bêta privée; elle ne remplace pas les procédures internes de sécurité.")
