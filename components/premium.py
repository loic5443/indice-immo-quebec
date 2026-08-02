"""Clear, payment-free Premium proposition for the private beta."""
import streamlit as st
from components.account import current_user,is_authenticated
from data.database import DATABASE_PATH
from repositories.sqlite_repository import SQLiteRepository

def show_premium():
 st.markdown("<section class='hero-image-panel'><div class='hero-content'><p class='hero-eyebrow notranslate'>IMMORADAR PREMIUM</p><h1>Plus d'outils, toujours expliqués.</h1><p class='hero-copy'>Préparez vos projets avec des rapports, scénarios et alertes en préparation.</p></div></section>",unsafe_allow_html=True)
 st.info("Premium est actuellement en préparation. Aucun paiement n'est demandé pendant la bêta privée.")
 free,premium=st.columns(2)
 with free: st.markdown("<article class='plan-card'><h2>Gratuit</h2><p><b>1 estimation complète par mois</b></p><p>Analyse financière · résultats expliqués · aperçu d'alertes verrouillé.</p><span class='data-pill real'>Disponible</span></article>",unsafe_allow_html=True)
 with premium: st.markdown("<article class='plan-card premium-card'><h2 class='notranslate'>Premium</h2><p><b>Tarif à confirmer</b></p><p>Estimations illimitées · historique · PDF · scénarios avancés · alertes personnalisées.</p><span class='data-pill simulated'>Expérimental / bientôt disponible</span></article>",unsafe_allow_html=True)
 st.subheader("Ce qui arrive avec Premium")
 st.dataframe([{"Fonction":"Rapports PDF complets","Statut":"Disponible"},{"Fonction":"Alertes personnalisées","Statut":"Expérimental"},{"Fonction":"Comparaison de villes, données enrichies, Radar des occasions","Statut":"Bientôt disponible"}],hide_index=True,width="stretch")
 if not is_authenticated(): st.button("Se connecter pour rejoindre la liste",disabled=True)
 else:
  user=current_user()
  with SQLiteRepository(DATABASE_PATH)._connect() as c: interest=c.execute("SELECT 1 FROM premium_interest WHERE user_id=?",(user['id'],)).fetchone()
  consent=st.checkbox("Je souhaite être avisé localement du lancement Premium",value=bool(interest))
  if st.button("M'avertir au lancement"):
   with SQLiteRepository(DATABASE_PATH)._connect() as c,c:
    if consent:c.execute("INSERT INTO premium_interest(user_id,consent) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET consent=1",(user['id'],));st.success("Votre intérêt est enregistré localement.")
    else:c.execute("DELETE FROM premium_interest WHERE user_id=?",(user['id'],));st.info("Vous avez été retiré de la liste.")
