import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from components.charts import show_market_chart
from components.header import show_header
from components.premium import show_premium
from components.sidebar import show_sidebar
from data.economic_data import get_canada_rate, get_inflation, get_unemployment


st.set_page_config(page_title="ImmoRadar", page_icon="🏠", layout="wide")

with open("styles/main.css", encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

page, market, mode, ville, type_propriete, prix, mise, revenu = show_sidebar()

if market == "Québec / Canada":
    taux_auto, taux_est_reel = get_canada_rate()
    inflation_auto, chomage_auto = get_inflation(), get_unemployment()
else:
    taux_auto, inflation_auto, chomage_auto = 5.25, 3.0, 4.2
    taux_est_reel = False

if mode == "Simulation personnalisée":
    taux = st.sidebar.slider("Taux d’intérêt (%)", 0.0, 12.0, float(taux_auto))
    inflation = st.sidebar.slider("Inflation (%)", 0.0, 12.0, float(inflation_auto))
    chomage = st.sidebar.slider("Chômage (%)", 0.0, 15.0, float(chomage_auto))
else:
    taux, inflation, chomage = taux_auto, inflation_auto, chomage_auto

ratio_mise = mise / prix * 100
ratio_prix_revenu = prix / revenu
score = 100 - taux * 4 - inflation * 2 - chomage * 1.5
score += 5 if ratio_mise >= 20 else -8 if ratio_mise < 10 else 0
score += -10 if ratio_prix_revenu > 6 else 5 if ratio_prix_revenu < 4 else 0
score += {"Duplex": 3, "Triplex": 5, "Immeuble locatif": 7, "Condo": -2}.get(type_propriete, 0)
score = max(0, min(100, round(score, 1)))

if score >= 75:
    statut, message = "🟢 Marché favorable", "Les conditions semblent intéressantes. Comparez les propriétés et conservez une marge de sécurité."
elif score >= 50:
    statut, message = "🟡 Marché prudent", "Le marché demande de la prudence : comparez, négociez et évitez de surpayer."
else:
    statut, message = "🔴 Marché risqué", "Les conditions sont difficiles. Réduire le budget ou attendre peut être plus prudent."

analyse = [
    "Les taux élevés augmentent les paiements hypothécaires." if taux >= 5 else "Les taux sont relativement acceptables pour financer une propriété.",
    "L’inflation réduit le pouvoir d’achat." if inflation >= 3 else "L’inflation semble stable.",
    "Le chômage élevé peut ralentir la demande immobilière." if chomage >= 6 else "Le marché de l’emploi semble solide.",
    "La mise de fonds est faible, ce qui augmente le risque." if ratio_mise < 10 else "La mise de fonds est solide, ce qui réduit le risque." if ratio_mise >= 20 else "La mise de fonds se situe dans une zone intermédiaire.",
    "Le prix est élevé par rapport au revenu annuel." if ratio_prix_revenu > 6 else "Le prix semble raisonnable par rapport au revenu annuel.",
]
if type_propriete in {"Duplex", "Triplex", "Immeuble locatif"}:
    analyse.append("Ce type de propriété peut offrir un potentiel locatif intéressant.")

if page == "Premium":
    show_premium(score, ville, prix, mise, revenu, taux, inflation, chomage)
    st.stop()

show_header()
st.divider()

st.subheader("Votre radar immobilier")
metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Score ImmoRadar", f"{score}/100")
metric2.metric("Taux directeur", f"{taux:.2f} %", "Donnée réelle" if taux_est_reel and mode == "Données automatiques" else "Exemple / simulation")
metric3.metric("Inflation", f"{inflation:.1f} %", "Exemple / simulation")
metric4.metric("Chômage", f"{chomage:.1f} %", "Exemple / simulation")

left, right = st.columns([1.25, 1])
with left:
    st.subheader(statut)
    (st.success if score >= 75 else st.warning if score >= 50 else st.error)(message)
    st.subheader("Ce que le score prend en compte")
    for point in analyse:
        st.write(f"• {point}")
    st.caption("Le score est un indicateur éducatif construit par ImmoRadar, pas une recommandation d’achat ou de vente.")

with right:
    st.subheader("Indicateur visuel")
    data = pd.DataFrame({"Zone": ["Risque", "Prudence", "Favorable", "Votre score"], "Valeur": [40, 60, 75, score]})
    fig = px.bar(data, x="Zone", y="Valeur", text="Valeur", title="Score de contexte immobilier")
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827", font_color="white", title_font_size=20)
    st.plotly_chart(fig, width="stretch")
    st.subheader("Résumé du projet")
    st.info(f"Marché : {market}\n\nVille : {ville}\n\nType : {type_propriete}\n\nPrix : {prix:,} $\n\nMise de fonds : {mise:,} $\n\nRevenu annuel : {revenu:,} $")

st.divider()
show_market_chart(ville)
st.divider()

st.subheader("Alertes ImmoRadar")
st.write("Recevez une notification lorsque les indicateurs suivis évoluent. Cette fonctionnalité utilise votre configuration Brevo existante si elle est disponible.")
email = st.text_input("Votre adresse courriel", placeholder="vous@exemple.com")
if st.button("Recevoir les alertes"):
    if not email or "@" not in email:
        st.error("Veuillez saisir une adresse courriel valide.")
    elif "BREVO_API_KEY" not in st.secrets:
        st.info("Les alertes ne sont pas configurées dans cette version. Aucune adresse n’a été envoyée.")
    else:
        try:
            response = requests.post(
                "https://api.brevo.com/v3/contacts",
                headers={"accept": "application/json", "api-key": st.secrets["BREVO_API_KEY"], "content-type": "application/json"},
                data=json.dumps({"email": email, "updateEnabled": True}),
                timeout=10,
            )
            if response.status_code in {200, 201, 204}:
                st.success("Adresse courriel enregistrée avec succès.")
            else:
                st.error("Impossible d’enregistrer l’adresse pour le moment.")
        except requests.RequestException:
            st.error("Le service d’alertes est temporairement inaccessible.")

rapport = f"""RAPPORT IMMO RADAR\n\nDate : {datetime.now().strftime('%Y-%m-%d')}\n\nMarché : {market}\nVille : {ville}\nType : {type_propriete}\n\nScore : {score}/100\nStatut : {statut}\n\nDonnées économiques :\n- Taux : {taux}% ({'réel' if taux_est_reel and mode == 'Données automatiques' else 'exemple ou simulation'})\n- Inflation : {inflation}% (exemple ou simulation)\n- Chômage : {chomage}% (exemple ou simulation)\n\nDonnées financières :\n- Prix : {prix}$\n- Mise de fonds : {mise}$ ({ratio_mise:.1f}%)\n- Revenu annuel : {revenu}$\n- Ratio prix/revenu : {ratio_prix_revenu:.1f}\n\nAnalyse :\n{chr(10).join('- ' + point for point in analyse)}\n\nNote : rapport éducatif; il ne remplace pas un conseil financier professionnel.\n"""
st.download_button("📥 Télécharger le rapport ImmoRadar", data=rapport, file_name="rapport_immoradar.txt", mime="text/plain")
