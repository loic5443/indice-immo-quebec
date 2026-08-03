"""About page focused on product value and transparent decision support."""
import streamlit as st
from components.sidebar import go_to

def show_about() -> None:
    st.markdown("<p class='eyebrow notranslate'>À PROPOS D'IMMORADAR</p>", unsafe_allow_html=True)
    st.title("Comprendre les chiffres avant une grande décision.")
    st.markdown("<p class='section-intro'>ImmoRadar rend l'analyse immobilière plus simple, compréhensible et utile. Il rassemble vos hypothèses, les calculs financiers et les données disponibles pour mieux évaluer une propriété.</p>", unsafe_allow_html=True)
    columns=st.columns(3)
    for column,title,copy in zip(columns,["1. Vos informations","2. Des calculs expliqués","3. Vos prochaines vérifications"],["Vous gardez le contrôle sur les renseignements saisis.","Les résultats présentent d'abord ce qu'ils signifient, puis les ratios techniques.","Les forces, risques et données manquantes sont visibles."]):
        with column: st.markdown(f"<article class='benefit-card'><h3>{title}</h3><p>{copy}</p></article>",unsafe_allow_html=True)
    st.markdown("<div class='section-space'></div><h2>Un outil conçu pour mieux préparer vos décisions</h2><p>ImmoRadar vous aide à comprendre les chiffres, à repérer les forces et les risques et à préparer vos échanges avec les professionnels concernés par votre transaction.</p><h2>Des données transparentes</h2><p>Chaque donnée externe affiche sa source, sa date et sa fraîcheur. Les données non disponibles ne sont jamais remplacées par des chiffres inventés.</p>",unsafe_allow_html=True)
    a,b,_=st.columns([1,1,2]);a.button("Commencer une analyse",type="primary",on_click=go_to,args=("Analyse immobilière",));b.button("Découvrir Premium",on_click=go_to,args=("Premium",))
    st.caption("ImmoRadar 0.7.0 — bêta privée. Outil d'aide à la décision : vérifiez les renseignements importants avant une transaction immobilière.")
