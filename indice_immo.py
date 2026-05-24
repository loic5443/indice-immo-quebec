import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
from components.premium import show_premium
from components.charts import show_market_chart
from datetime import datetime
from components.header import show_header
from components.sidebar import show_sidebar
from data.economic_data import (
    get_canada_rate,
    get_inflation,
    get_unemployment
)

st.set_page_config(page_title="ImmoRadar", page_icon="🏠", layout="wide")

with open("styles/main.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

show_header()
st.divider()

(
    market,
    mode,
    ville,
    type_propriete,
    prix,
    mise,
    revenu
) = show_sidebar()

if market == "Québec / Canada":

    taux_auto = get_canada_rate()
    inflation_auto = get_inflation()
    chomage_auto = get_unemployment()

else:

    taux_auto = 5.25
    inflation_auto = 3.0
    chomage_auto = 4.2

if mode == "Simulation personnalisée":

    taux = st.sidebar.slider(
        "Taux d’intérêt (%)",
        0.0,
        12.0,
        float(taux_auto)
    )

    inflation = st.sidebar.slider(
        "Inflation (%)",
        0.0,
        12.0,
        float(inflation_auto)
    )

    chomage = st.sidebar.slider(
        "Chômage (%)",
        0.0,
        15.0,
        float(chomage_auto)
    )

else:

    taux = taux_auto
    inflation = inflation_auto
    chomage = chomage_auto

ratio_mise = (mise / prix) * 100
ratio_prix_revenu = prix / revenu

score = 100 - (taux * 4) - (inflation * 2) - (chomage * 1.5)

if ratio_mise < 10:
    score -= 8
elif ratio_mise >= 20:
    score += 5

if ratio_prix_revenu > 6:
    score -= 10
elif ratio_prix_revenu < 4:
    score += 5

if type_propriete == "Duplex":
    score += 3
elif type_propriete == "Triplex":
    score += 5
elif type_propriete == "Immeuble locatif":
    score += 7
elif type_propriete == "Condo":
    score -= 2

score = max(0, min(100, round(score, 1)))

if score >= 75:
    statut = "🟢 Marché favorable"
    message = "Les conditions semblent intéressantes. Acheter peut être une bonne option si le prix est raisonnable."
elif score >= 50:
    statut = "🟡 Marché prudent"
    message = "Le marché demande de la prudence. Il faut comparer, négocier et éviter de surpayer."
else:
    statut = "🔴 Marché risqué"
    message = "Les conditions sont difficiles. Attendre ou réduire le budget pourrait être plus prudent."

col1, col2, col3, col4 = st.columns(4)
col1.metric("Score ImmoRadar", f"{score}/100")
col2.metric("Taux", f"{taux}%")
col3.metric("Inflation", f"{inflation}%")
col4.metric("Chômage", f"{chomage}%")

st.divider()

left, right = st.columns([1.3, 1])

with left:
    st.subheader(statut)

    if score >= 75:
        st.success(message)
    elif score >= 50:
        st.warning(message)
    else:
        st.error(message)

    st.subheader("🤖 Analyse intelligente")

    analyse = []

    if taux >= 5:
        analyse.append("Les taux d’intérêt élevés augmentent les paiements hypothécaires.")
    else:
        analyse.append("Les taux sont relativement acceptables pour financer une propriété.")

    if inflation >= 3:
        analyse.append("L’inflation réduit le pouvoir d’achat des acheteurs.")
    else:
        analyse.append("L’inflation semble stable.")

    if chomage >= 6:
        analyse.append("Le chômage élevé peut ralentir la demande immobilière.")
    else:
        analyse.append("Le marché de l’emploi semble solide.")

    if ratio_mise < 10:
        analyse.append("La mise de fonds est faible, ce qui augmente le risque.")
    elif ratio_mise >= 20:
        analyse.append("La mise de fonds est solide, ce qui réduit le risque.")

    if ratio_prix_revenu > 6:
        analyse.append("Le prix est élevé comparé au revenu annuel.")
    else:
        analyse.append("Le prix semble raisonnable comparé au revenu annuel.")

    if type_propriete in ["Duplex", "Triplex", "Immeuble locatif"]:
        analyse.append("Ce type de propriété peut offrir un potentiel locatif intéressant.")

    for a in analyse:
        st.write("• " + a)

    st.subheader("💡 Recommandation")
    st.write(message)

with right:

    st.subheader("📊 Indicateur visuel")

    data = pd.DataFrame({
        "Zone": ["Risque", "Prudence", "Favorable", "Votre score"],
        "Valeur": [40, 60, 75, score]
    })

    fig = px.bar(
        data,
        x="Zone",
        y="Valeur",
        text="Valeur",
        title="Score de risque immobilier"
    )

    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="white",
        title_font_size=22
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🏘️ Résumé")

    st.info(f"""
Marché : {market}

Ville : {ville}

Type : {type_propriete}

Prix : {prix:,}$

Mise de fonds : {mise:,}$

Revenu annuel : {revenu:,}$
""")

st.divider()

show_market_chart(ville)

st.divider()

st.subheader("📩 Alertes ImmoRadar")

st.write("Recevez des alertes quand le marché immobilier devient plus favorable.")

st.divider()

show_premium()

email = st.text_input("Votre email")

if st.button("Recevoir les alertes"):

    API_KEY = st.secrets["BREVO_API_KEY"]

    url = "https://api.brevo.com/v3/contacts"

    headers = {
        "accept": "application/json",
        "api-key": API_KEY,
        "content-type": "application/json"
    }

    data = {
        "email": email,
        "updateEnabled": True
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code in [200, 201, 204]:
        st.success("✅ Email enregistré avec succès!")
    else:
        st.error("❌ Erreur lors de l'inscription.")


rapport = f"""
RAPPORT IMMRADAR

Date : {datetime.now().strftime('%Y-%m-%d')}

Marché : {market}
Ville : {ville}
Type : {type_propriete}

Score : {score}/100
Statut : {statut}

Données économiques :
- Taux : {taux}%
- Inflation : {inflation}%
- Chômage : {chomage}%

Données financières :
- Prix : {prix}$
- Mise de fonds : {mise}$
- Revenu annuel : {revenu}$
- Mise de fonds : {round(ratio_mise, 1)}%
- Ratio prix/revenu : {round(ratio_prix_revenu, 1)}

Analyse :
{chr(10).join("- " + a for a in analyse)}

Note : Ce rapport est éducatif et ne remplace pas un conseil financier professionnel.
"""

st.download_button(
    "📥 Télécharger le rapport ImmoRadar",
    data=rapport,
    file_name="rapport_immoradar.txt",
    mime="text/plain"
)

