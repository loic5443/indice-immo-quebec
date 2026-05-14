import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Indice Immobilier Québec",
    page_icon="🏠",
    layout="centered"
)

def get_taux_banque_canada():
    try:
        url = "https://www.bankofcanada.ca/valet/observations/V39079/json"
        data = requests.get(url, timeout=10).json()
        last = data["observations"][-1]
        return float(last["V39079"]["v"])
    except:
        return 5.0

taux = get_taux_banque_canada()
inflation = 3.0
chomage = 6.0

score = 100 - (taux * 4) - (inflation * 2) - (chomage * 1.5)
score = round(score, 1)

st.title("🏠 Indice Immobilier Québec")
st.write("Outil simple pour évaluer si le marché immobilier est favorable ou risqué.")

st.divider()

st.subheader("📊 Données économiques")

col1, col2, col3 = st.columns(3)
col1.metric("Taux d’intérêt", f"{taux}%")
col2.metric("Inflation", f"{inflation}%")
col3.metric("Chômage", f"{chomage}%")

st.divider()

st.subheader("📈 Score immobilier")
st.metric("Score", f"{score}/100")

graph_data = pd.DataFrame({
    "Indicateur": ["Score actuel", "Zone prudence", "Zone favorable"],
    "Valeur": [score, 40, 70]
})

st.bar_chart(graph_data.set_index("Indicateur"))

if score > 70:
    statut = "🟢 Marché favorable"
    analyse = "Les conditions sont plutôt bonnes. Acheter peut être intéressant si le prix est raisonnable."
elif score > 40:
    statut = "🟡 Marché incertain"
    analyse = "Le marché demande de la prudence. Il vaut mieux comparer, négocier et éviter de se précipiter."
else:
    statut = "🔴 Marché risqué"
    analyse = "Les conditions économiques sont difficiles. Acheter maintenant peut être risqué."

st.subheader(statut)
st.write(analyse)

st.divider()

st.subheader("🧠 Analyse automatique")

if taux >= 5:
    st.write("⚠️ Les taux sont élevés : les hypothèques coûtent plus cher.")
else:
    st.write("✅ Les taux sont acceptables : le financement est plus facile.")

if inflation >= 3:
    st.write("⚠️ L’inflation réduit le pouvoir d’achat.")
else:
    st.write("✅ L’inflation est relativement stable.")

if chomage >= 6:
    st.write("⚠️ Le chômage est élevé : cela peut ralentir la demande.")
else:
    st.write("✅ Le marché de l’emploi semble solide.")

st.divider()

st.subheader("📄 Rapport téléchargeable")

rapport = f"""
RAPPORT - INDICE IMMOBILIER QUÉBEC

Score immobilier : {score}/100
Statut : {statut}

Données utilisées :
- Taux d’intérêt : {taux}%
- Inflation : {inflation}%
- Chômage : {chomage}%

Analyse :
{analyse}

Note :
Ce rapport est un prototype éducatif. Il ne remplace pas un conseil financier professionnel.
"""

st.download_button(
    label="📥 Télécharger le rapport",
    data=rapport,
    file_name="rapport_indice_immobilier_quebec.txt",
    mime="text/plain"
)

st.caption("Version prototype — outil éducatif, pas un conseil financier officiel.")