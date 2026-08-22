"""Private, local feedback panel available through the secondary navigation."""

import streamlit as st

from components.account import current_user, is_authenticated
from components.sidebar import go_to
from data.database import DATABASE_PATH
from services.feedback_service import list_feedback, submit_feedback


def show_feedback() -> None:
    st.markdown("<p class='eyebrow'>VOTRE AVIS</p>", unsafe_allow_html=True)
    st.title("Aidez-nous à améliorer ImmoRadar")
    st.markdown("<p class='section-intro'>Décrivez ce qui vous a aidé, surpris ou bloqué. Votre retour reste associé à votre compte et sert uniquement à améliorer le produit pendant la bêta.</p>", unsafe_allow_html=True)
    if not is_authenticated():
        st.info("Connectez-vous pour envoyer et retrouver vos retours.")
        st.button("Accéder à Mon compte", type="primary", on_click=go_to, args=("Mon compte",))
        return

    st.caption("N’indiquez pas de mot de passe, de code d’invitation, d’adresse complète ou de montants financiers dans votre message.")
    with st.form("feedback"):
        page = st.selectbox("Où étiez-vous?", ["Accueil", "Analyse", "Marché", "Premium", "Mon compte"])
        category = st.selectbox("Quel type de retour souhaitez-vous partager?", ["Incompréhension", "Erreur technique", "Donnée incorrecte", "Résultat surprenant", "Suggestion", "Autre"])
        usefulness = st.slider("À quel point ImmoRadar vous a-t-il été utile?", 1, 5, 3, help="1 = peu utile · 5 = très utile")
        comment = st.text_area("Votre retour", placeholder="Expliquez ce que vous avez observé, sans renseignements sensibles.", max_chars=2000)
        contact = st.checkbox("Vous pouvez me contacter au sujet de ce retour")
        sent = st.form_submit_button("Envoyer mon retour", type="primary", use_container_width=True)
    if sent:
        try:
            submit_feedback(current_user()["id"], page, category, usefulness, comment, contact, DATABASE_PATH)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("Merci, votre retour a été enregistré dans votre espace ImmoRadar.")

    st.markdown("<div class='section-space compact-space'></div><h2>Mes retours</h2>", unsafe_allow_html=True)
    rows = list_feedback(current_user()["id"], DATABASE_PATH)
    if not rows:
        st.info("Vous n’avez encore envoyé aucun retour.")
        return
    st.caption("Vous voyez uniquement vos propres retours et leur statut de traitement.")
    st.dataframe(rows, hide_index=True, width="stretch")
