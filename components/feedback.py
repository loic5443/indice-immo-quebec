"""Accessible local feedback panel available from every page through the sidebar."""
import streamlit as st
from components.account import current_user,is_authenticated
from data.database import DATABASE_PATH
from services.feedback_service import submit_feedback,list_feedback

def show_feedback():
 st.title("Donner mon avis")
 if not is_authenticated(): st.info("Connectez-vous pour envoyer un retour.");return
 with st.form("feedback"):
  page=st.selectbox("Page concernée",["Accueil","Analyse","Marchés","Premium","Compte"]);category=st.selectbox("Catégorie",["Incompréhension","Erreur technique","Donnée incorrecte","Résultat surprenant","Suggestion","Autre"]);usefulness=st.slider("Utilité",1,5,3);comment=st.text_area("Commentaire",max_chars=2000);contact=st.checkbox("Vous pouvez me contacter")
  sent=st.form_submit_button("Envoyer")
 if sent:
  try: submit_feedback(current_user()["id"],page,category,usefulness,comment,contact,DATABASE_PATH);st.success("Merci, votre retour a été enregistré.")
  except ValueError as error: st.error(str(error))
 st.subheader("Mes retours");st.dataframe(list_feedback(current_user()["id"],DATABASE_PATH),hide_index=True,width="stretch")
