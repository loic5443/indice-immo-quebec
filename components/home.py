"""Modern product landing page using an offline-safe local real-estate visual."""
import base64
from pathlib import Path
import streamlit as st
from components.sidebar import go_to

IMAGE=Path(__file__).resolve().parents[1]/"assets"/"images"/"immoradar-hero.png"
@st.cache_data(show_spinner=False)
def _hero():
 if not IMAGE.exists(): return ""
 return "background-image:linear-gradient(95deg,rgba(7,23,45,.96),rgba(7,23,45,.62)),url('data:image/png;base64,"+base64.b64encode(IMAGE.read_bytes()).decode()+"');"
def show_home():
 st.markdown(f"<section class='hero-image-panel' style=\"{_hero()}\"><div class='hero-content'><p class='hero-eyebrow notranslate'>IMMORADAR</p><h1>Comprenez votre projet immobilier avant de vous engager.</h1><p class='hero-copy'>Vos hypothèses, des calculs clairs et des résultats expliqués au même endroit.</p><p class='hero-proof'>Transparent · Adapté à votre projet · Facile à relire</p></div></section>",unsafe_allow_html=True)
 a,b,_=st.columns([1,1,2]);a.button("Commencer une analyse",type="primary",on_click=go_to,args=("Analyse immobilière",),use_container_width=True);b.button("Découvrir Premium",on_click=go_to,args=("Premium",),use_container_width=True)
 st.markdown("<div class='section-space'></div><p class='eyebrow'>APERÇU</p><h2>Un résultat qui explique ce qui compte.</h2>",unsafe_allow_html=True)
 c1,c2=st.columns([1.1,1])
 with c1: st.markdown("<article class='benefit-card'><span class='data-pill simulated'>Exemple d'interface</span><h3>Score ImmoRadar · 74 / 100</h3><p><b>Confiance :</b> 68 / 100 · Qualité et complétude des informations.</p><p><b>Flux mensuel :</b> aperçu de résultat, non une donnée réelle.</p></article>",unsafe_allow_html=True)
 with c2: st.markdown("<article class='benefit-card'><h3>Lecture rapide</h3><p>✓ Point fort : revenus et dépenses visibles.</p><p>↗ À vérifier : informations manquantes à confirmer.</p></article>",unsafe_allow_html=True)
 st.markdown("<div class='section-space'></div><p class='eyebrow'>COMMENT ÇA FONCTIONNE</p><h2>Trois étapes, sans jargon inutile.</h2>",unsafe_allow_html=True)
 for col,(n,t,p) in zip(st.columns(3),[("01","Décrivez la propriété","Ajoutez les informations que vous avez."),("02","Ajoutez vos informations","Financement, revenus et dépenses."),("03","Comprenez le résultat","Voyez les forces, risques et prochaines vérifications.")]):
  with col: st.markdown(f"<article class='step-card'><span class='step-number'>{n}</span><h3>{t}</h3><p>{p}</p></article>",unsafe_allow_html=True)
 st.markdown("<div class='section-space'></div><h2>Pourquoi ImmoRadar</h2>",unsafe_allow_html=True)
 for col,(t,p) in zip(st.columns(4),[("Analyse expliquée","Une conclusion claire avant les ratios."),("Hypothèses transparentes","Vous voyez ce qui alimente chaque résultat."),("Scénarios","Testez vos hypothèses sans prédire l'avenir."),("Sauvegarde et rapport","Gardez une trace utile de votre réflexion.")]):
  with col: st.markdown(f"<article class='benefit-card'><h3>{t}</h3><p>{p}</p></article>",unsafe_allow_html=True)
 st.markdown("<div class='section-space'></div><section class='premium-notice'><p class='eyebrow notranslate'>ALERTES PREMIUM</p><h2>Gardez une longueur d’avance</h2><p>Suivez les changements qui peuvent influencer vos décisions grâce aux alertes personnalisées ImmoRadar.</p><p>🔔 Aperçus : changement de taux · propriété suivie · marché à surveiller. Aucun envoi actif pendant la bêta.</p></section>",unsafe_allow_html=True);st.button("Découvrir Premium",on_click=go_to,args=("Premium",),key="home_premium")
 st.markdown("<div class='section-space'></div><h2>Sources et transparence</h2><p>Vos hypothèses restent distinctes des calculs et des données externes. Chaque indicateur officiel affiche sa source, sa date et sa fraîcheur; une donnée absente n'est pas inventée.</p><div class='final-cta'><h2>Prêt à examiner votre prochain projet?</h2><p>Commencez avec les informations que vous avez déjà.</p></div>",unsafe_allow_html=True);st.button("Commencer une analyse",type="primary",on_click=go_to,args=("Analyse immobilière",),key="home_final")
