import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="ImmoRadar",
    page_icon="🏠",
    layout="wide"
)

# ---------- STYLE ----------
st.markdown("""
<style>
.main {
    background-color: #f7f9fc;
}
.big-title {
    font-size: 48px;
    font-weight: 800;
    color: #0b1f3a;
}
.subtitle {
    font-size: 20px;
    color: #4b5563;
}
.card {
    padding: 25px;
    border-radius: 18px;
    background-color: white;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}
.score {
    font-size: 52px;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)

# ---------- DATA ----------
def get_canada_rate():
    try:
        url = "https://www.bankofcanada.ca/valet/observations/V39079/json"
        data = requests.get(url, timeout=10).json()
        return float(data["observations"][-1]["V39079"]["v"])
    except:
        return 5.0

def get_us_rate():
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        return 5.25
    except:
        return 5.25

# ---------- HEADER ----------
st.markdown('<div class="big-title">🏠 ImmoRadar</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Analyse intelligente du marché immobilier — Québec, Canada et États-Unis.</div>', unsafe_allow_html=True)

st.divider()

# ---------- SIDEBAR ----------
st.sidebar.title("⚙️ Paramètres")

market = st.sidebar.selectbox(
    "Marché",
    ["Québec / Canada", "États-Unis"]
)

mode = st.sidebar.radio(
    "Mode",
    ["Données automatiques", "Simulation personnalisée"]
)

if market == "Québec / Canada":
    base_rate = get_canada_rate()
    default_inflation = 3.0
    default_unemployment = 6.0
else:
    base_rate = get_us_rate()
    default_inflation = 3.2
    default_unemployment = 4.0

if mode == "Simulation personnalisée":
    taux = st.sidebar.slider("Taux d’intérêt (%)", 0.0, 12.0, float(base_rate))
    inflation = st.sidebar.slider("Inflation (%)", 0.0, 12.0, float(default_inflation))
    chomage = st.sidebar.slider("Chômage (%)", 0.0, 15.0, float(default_unemployment))
else:
    taux = base_rate
    inflation = default_inflation
    chomage = default_unemployment

prix_propriete = st.sidebar.number_input("Prix propriété ($)", value=400000, step=10000)
mise_de_fonds = st.sidebar.number_input("Mise de fonds ($)", value=40000, step=5000)
revenu_annuel = st.sidebar.number_input("Revenu annuel ($)", value=70000, step=5000)

# ---------- CALCUL ----------
score = 100 - (taux * 4) - (inflation * 2) - (chomage * 1.5)

ratio_mise = (mise_de_fonds / prix_propriete) * 100
ratio_prix_revenu = prix_propriete / revenu_annuel

if ratio_mise < 10:
    score -= 8
elif ratio_mise >= 20:
    score += 5

if ratio_prix_revenu > 6:
    score -= 10
elif ratio_prix_revenu < 4:
    score += 5

score = max(0, min(100, round(score, 1)))

# ---------- STATUS ----------
if score >= 75:
    statut = "🟢 Marché favorable"
    couleur = "success"
    resume = "Les conditions sont intéressantes. Acheter peut être une bonne option si le prix est raisonnable."
elif score >= 50:
    statut = "🟡 Marché incertain"
    couleur = "warning"
    resume = "Le marché demande de la prudence. Il faut comparer, négocier et éviter les décisions rapides."
else:
    statut = "🔴 Marché risqué"
    couleur = "error"
    resume = "Les conditions sont difficiles. Acheter maintenant peut être risqué si le budget est serré."

# ---------- MAIN METRICS ----------
col1, col2, col3, col4 = st.columns(4)

col1.metric("Score ImmoRadar", f"{score}/100")
col2.metric("Taux d’intérêt", f"{taux}%")
col3.metric("Inflation", f"{inflation}%")
col4.metric("Chômage", f"{chomage}%")

st.divider()

# ---------- RESULT ----------
left, right = st.columns([1.2, 1])

with left:
    st.subheader(statut)
    if couleur == "success":
        st.success(resume)
    elif couleur == "warning":
        st.warning(resume)
    else:
        st.error(resume)

    st.markdown("### 🧠 Analyse intelligente")

    analyse_points = []

    if taux >= 5:
        analyse_points.append("Les taux sont élevés, ce qui augmente le coût des paiements hypothécaires.")
    else:
        analyse_points.append("Les taux sont relativement acceptables, ce qui rend le financement plus facile.")

    if inflation >= 3:
        analyse_points.append("L’inflation réduit le pouvoir d’achat des acheteurs.")
    else:
        analyse_points.append("L’inflation est relativement stable.")

    if chomage >= 6:
        analyse_points.append("Le chômage plus élevé peut ralentir la demande immobilière.")
    else:
        analyse_points.append("Le marché de l’emploi semble assez solide.")

    if ratio_mise < 10:
        analyse_points.append("La mise de fonds est faible, donc le risque financier est plus élevé.")
    elif ratio_mise >= 20:
        analyse_points.append("La mise de fonds est solide, ce qui réduit le risque.")

    if ratio_prix_revenu > 6:
        analyse_points.append("Le prix de la propriété est élevé comparé au revenu annuel.")
    else:
        analyse_points.append("Le prix semble plus raisonnable comparé au revenu annuel.")

    for point in analyse_points:
        st.write("• " + point)

with right:
    st.markdown("### 📊 Indicateur visuel")

    graph_data = pd.DataFrame({
        "Zone": ["Risque", "Prudence", "Favorable", "Score actuel"],
        "Valeur": [40, 60, 75, score]
    })

    st.bar_chart(graph_data.set_index("Zone"))

# ---------- RECOMMANDATION ----------
st.divider()
st.subheader("💡 Recommandation")

if score >= 75:
    st.write("👉 Acheter peut être une bonne option, mais seulement si le prix est bon et que l’immeuble est bien analysé.")
elif score >= 50:
    st.write("👉 Le meilleur choix est souvent de négocier fortement, comparer plusieurs propriétés et éviter de surpayer.")
else:
    st.write("👉 Il vaut mieux attendre de meilleures conditions ou réduire le prix/projet avant d’acheter.")

# ---------- PREMIUM MOCKUP ----------
st.divider()
st.subheader("🔒 Fonctionnalités Premium à venir")

p1, p2, p3 = st.columns(3)

p1.info("📩 Alertes marché\n\nRecevoir une alerte quand le marché devient favorable.")
p2.info("🤖 Analyse IA avancée\n\nAnalyse personnalisée selon ville, budget et objectif.")
p3.info("📈 Historique complet\n\nSuivi des taux, inflation, chômage et score dans le temps.")

# ---------- REPORT ----------
st.divider()
st.subheader("📄 Rapport téléchargeable")

rapport = f"""
RAPPORT IMMRADAR

Date : {datetime.now().strftime("%Y-%m-%d")}
Marché : {market}

Score : {score}/100
Statut : {statut}

Données économiques :
- Taux d’intérêt : {taux}%
- Inflation : {inflation}%
- Chômage : {chomage}%

Données personnelles :
- Prix propriété : {prix_propriete}$
- Mise de fonds : {mise_de_fonds}$
- Revenu annuel : {revenu_annuel}$
- Mise de fonds : {round(ratio_mise, 1)}%
- Ratio prix/revenu : {round(ratio_prix_revenu, 1)}

Analyse :
{resume}

Points importants :
{chr(10).join("- " + p for p in analyse_points)}

Note :
Ce rapport est un prototype éducatif. Il ne remplace pas un conseil financier, hypothécaire ou immobilier professionnel.
"""

st.download_button(
    "📥 Télécharger le rapport ImmoRadar",
    data=rapport,
    file_name="rapport_immoradar.txt",
    mime="text/plain"
)

st.caption("ImmoRadar — Prototype SaaS immobilier éducatif.")