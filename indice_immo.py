import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from math import pow

st.set_page_config(
    page_title="ImmoRadar | Analyse immobilière intelligente",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 3rem; }
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
    color: white;
    padding: 36px;
    border-radius: 28px;
    margin-bottom: 26px;
    box-shadow: 0 20px 45px rgba(15, 23, 42, 0.25);
}
.hero h1 { font-size: 54px; margin-bottom: 8px; }
.hero p { font-size: 21px; color: #dbeafe; }
.badge {
    display: inline-block;
    padding: 7px 13px;
    background: rgba(255,255,255,0.15);
    border-radius: 999px;
    margin-right: 8px;
    font-size: 14px;
}
.card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 22px;
    padding: 24px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.07);
    margin-bottom: 18px;
}
.price-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 24px;
    min-height: 300px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.07);
}
.price-feature { margin: 8px 0; color: #334155; }
.cta-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 20px;
    padding: 22px;
}
.footer { color: #64748b; font-size: 13px; margin-top: 25px; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_canada_rate():
    try:
        url = "https://www.bankofcanada.ca/valet/observations/V39079/json"
        data = requests.get(url, timeout=10).json()
        obs = data.get("observations", [])
        if obs:
            return float(obs[-1]["V39079"]["v"])
    except Exception:
        pass
    return 5.0

@st.cache_data(ttl=3600)
def get_canada_rate_history():
    try:
        url = "https://www.bankofcanada.ca/valet/observations/V39079/json"
        data = requests.get(url, timeout=10).json()
        rows = []
        for o in data.get("observations", [])[-24:]:
            rows.append({"Date": o["d"], "Taux": float(o["V39079"]["v"])})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame({
            "Date": ["M-5", "M-4", "M-3", "M-2", "M-1", "Actuel"],
            "Taux": [5.0, 5.0, 4.75, 4.5, 3.75, 2.25]
        })

def default_macro(market):
    if market == "Québec / Canada":
        return get_canada_rate(), 3.0, 6.0
    return 5.25, 3.2, 4.0

def mortgage_payment(principal, annual_rate, years=25):
    if principal <= 0:
        return 0
    monthly_rate = annual_rate / 100 / 12
    n = years * 12
    if monthly_rate == 0:
        return principal / n
    return principal * (monthly_rate * pow(1 + monthly_rate, n)) / (pow(1 + monthly_rate, n) - 1)

def risk_label(score):
    if score >= 78:
        return "🟢 Très favorable", "success"
    if score >= 65:
        return "🟢 Favorable", "success"
    if score >= 50:
        return "🟡 Prudent", "warning"
    if score >= 35:
        return "🟠 Risqué", "warning"
    return "🔴 Très risqué", "error"

def calculate_score(taux, inflation, chomage, price, down, income, property_type, objective, monthly_rent, expenses):
    score = 100
    score -= taux * 4.0
    score -= inflation * 2.0
    score -= chomage * 1.5

    down_ratio = (down / price) * 100 if price else 0
    price_income_ratio = price / income if income else 99

    if down_ratio < 5:
        score -= 14
    elif down_ratio < 10:
        score -= 9
    elif down_ratio >= 20:
        score += 7

    if price_income_ratio > 7:
        score -= 14
    elif price_income_ratio > 5:
        score -= 8
    elif price_income_ratio < 4:
        score += 6

    if property_type == "Condo":
        score -= 2
    elif property_type == "Duplex":
        score += 4
    elif property_type == "Triplex":
        score += 6
    elif property_type == "Immeuble locatif":
        score += 8

    mortgage = max(price - down, 0)
    monthly_payment = mortgage_payment(mortgage, taux)
    monthly_debt_ratio = monthly_payment / (income / 12) if income else 99

    if monthly_debt_ratio > 0.45:
        score -= 14
    elif monthly_debt_ratio > 0.35:
        score -= 8
    elif monthly_debt_ratio < 0.28:
        score += 5

    net_cashflow = monthly_rent - monthly_payment - expenses

    if objective in ["Investissement locatif", "Duplex / Triplex / Plex"]:
        if net_cashflow > 300:
            score += 8
        elif net_cashflow > 0:
            score += 4
        elif net_cashflow < -500:
            score -= 10
        elif net_cashflow < 0:
            score -= 5

    return max(0, min(100, round(score, 1))), {
        "down_ratio": down_ratio,
        "price_income_ratio": price_income_ratio,
        "monthly_payment": monthly_payment,
        "monthly_debt_ratio": monthly_debt_ratio,
        "net_cashflow": net_cashflow
    }

def make_analysis(market, city, property_type, objective, score, taux, inflation, chomage, metrics):
    points = []

    if taux >= 5:
        points.append("Les taux d’intérêt sont élevés, ce qui augmente fortement les paiements hypothécaires.")
    elif taux >= 3.5:
        points.append("Les taux sont modérés : le financement reste possible, mais il faut éviter de surpayer.")
    else:
        points.append("Les taux sont relativement favorables, ce qui améliore la capacité d’achat.")

    if inflation >= 3:
        points.append("L’inflation réduit le pouvoir d’achat et peut augmenter les coûts de rénovation, taxes et assurances.")
    else:
        points.append("L’inflation semble plus stable, ce qui rend les projections plus prévisibles.")

    if chomage >= 6:
        points.append("Le chômage plus élevé peut ralentir la demande et augmenter la prudence sur le marché.")
    else:
        points.append("Le marché de l’emploi est relativement solide, ce qui soutient la demande immobilière.")

    if metrics["down_ratio"] < 10:
        points.append("La mise de fonds est faible : ton risque financier est plus élevé.")
    elif metrics["down_ratio"] >= 20:
        points.append("La mise de fonds est solide : cela réduit ton risque et peut améliorer le financement.")

    if metrics["price_income_ratio"] > 6:
        points.append("Le prix est élevé comparé au revenu annuel, donc la marge de sécurité est faible.")
    else:
        points.append("Le prix est raisonnable comparé au revenu annuel, ce qui améliore le profil du projet.")

    if property_type in ["Duplex", "Triplex", "Immeuble locatif"]:
        points.append("Le potentiel locatif peut aider à compenser les paiements, mais il faut valider les loyers réels.")

    if metrics["net_cashflow"] < 0 and objective in ["Investissement locatif", "Duplex / Triplex / Plex"]:
        points.append("Le cashflow estimé est négatif : le projet doit être négocié ou mieux financé.")
    elif metrics["net_cashflow"] > 0 and objective in ["Investissement locatif", "Duplex / Triplex / Plex"]:
        points.append("Le cashflow estimé est positif : c’est un bon signe pour un investisseur.")

    if score >= 78:
        conclusion = f"Pour {city}, le projet semble très intéressant, surtout si l’inspection et le prix local confirment la valeur."
    elif score >= 65:
        conclusion = f"Pour {city}, le projet semble favorable, mais il faut comparer avec des propriétés similaires."
    elif score >= 50:
        conclusion = f"Pour {city}, le projet est possible, mais la négociation est importante."
    elif score >= 35:
        conclusion = f"Pour {city}, le projet comporte plusieurs risques. Il faut réduire le prix, augmenter la mise de fonds ou attendre."
    else:
        conclusion = f"Pour {city}, le projet est très risqué dans les conditions actuelles."

    return points, conclusion

st.sidebar.title("⚙️ Analyse ImmoRadar")

market = st.sidebar.selectbox("Marché", ["Québec / Canada", "États-Unis"])
mode = st.sidebar.radio("Données", ["Automatiques", "Simulation"])
city = st.sidebar.text_input("Ville", "Montréal" if market == "Québec / Canada" else "Miami")

objective = st.sidebar.selectbox(
    "Objectif",
    ["Achat personnel", "Investissement locatif", "Duplex / Triplex / Plex", "Analyse rapide du marché"]
)

property_type = st.sidebar.selectbox(
    "Type de propriété",
    ["Maison", "Condo", "Duplex", "Triplex", "Immeuble locatif"]
)

taux_auto, inflation_auto, chomage_auto = default_macro(market)

if mode == "Simulation":
    taux = st.sidebar.slider("Taux d’intérêt (%)", 0.0, 12.0, float(taux_auto), 0.05)
    inflation = st.sidebar.slider("Inflation (%)", 0.0, 12.0, float(inflation_auto), 0.1)
    chomage = st.sidebar.slider("Chômage (%)", 0.0, 15.0, float(chomage_auto), 0.1)
else:
    taux, inflation, chomage = taux_auto, inflation_auto, chomage_auto

st.sidebar.divider()

price = st.sidebar.number_input("Prix propriété ($)", min_value=50000, value=450000, step=10000)
down = st.sidebar.number_input("Mise de fonds ($)", min_value=0, value=60000, step=5000)
income = st.sidebar.number_input("Revenu annuel ($)", min_value=10000, value=85000, step=5000)

st.sidebar.divider()

monthly_rent = st.sidebar.number_input("Revenus locatifs mensuels ($)", min_value=0, value=0, step=100)
expenses = st.sidebar.number_input("Dépenses mensuelles estimées ($)", min_value=0, value=500, step=50)

score, metrics = calculate_score(
    taux, inflation, chomage, price, down, income,
    property_type, objective, monthly_rent, expenses
)

label, color = risk_label(score)
analysis_points, conclusion = make_analysis(
    market, city, property_type, objective, score,
    taux, inflation, chomage, metrics
)

st.markdown("""
<div class="hero">
    <span class="badge">SaaS immobilier</span>
    <span class="badge">Canada + USA</span>
    <span class="badge">Analyse intelligente</span>
    <h1>🏠 ImmoRadar</h1>
    <p>Décide plus vite, négocie mieux, évite les mauvais achats immobiliers.</p>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Score ImmoRadar", f"{score}/100", label)
c2.metric("Taux", f"{taux}%")
c3.metric("Inflation", f"{inflation}%")
c4.metric("Chômage", f"{chomage}%")

st.divider()

left, right = st.columns([1.45, 1])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader(label)

    if color == "success":
        st.success(conclusion)
    elif color == "warning":
        st.warning(conclusion)
    else:
        st.error(conclusion)

    st.markdown("### 🤖 Analyse intelligente")

    for p in analysis_points:
        st.write("• " + p)

    st.markdown("### 💡 Recommandation stratégique")

    if score >= 75:
        st.write("👉 Bonne base. Valide les comparables, l’inspection, les revenus locatifs et la marge de négociation.")
    elif score >= 50:
        st.write("👉 Ne te précipite pas. Négocie, compare plusieurs options et améliore ton financement si possible.")
    else:
        st.write("👉 Trop risqué pour l’instant. Réduis le budget, augmente la mise de fonds ou attends.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("💵 Analyse financière")

    f1, f2, f3 = st.columns(3)
    f1.metric("Paiement hypothécaire estimé", f"{metrics['monthly_payment']:,.0f}$/mois")
    f2.metric("Ratio paiement / revenu", f"{metrics['monthly_debt_ratio']*100:.1f}%")
    f3.metric("Cashflow estimé", f"{metrics['net_cashflow']:,.0f}$/mois")

    st.caption("Calcul estimatif simplifié. Les taxes, assurances, frais de condo et conditions bancaires réelles peuvent changer le résultat.")
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Indicateur de risque")

    gauge = pd.DataFrame({
        "Zone": ["Risque", "Prudence", "Favorable", "Très favorable", "Votre score"],
        "Valeur": [35, 50, 65, 78, score]
    })

    st.bar_chart(gauge.set_index("Zone"))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🏘️ Résumé du projet")

    st.info(f"""
📍 Marché : {market}

🏙️ Ville : {city}

🏠 Type : {property_type}

🎯 Objectif : {objective}

💰 Prix : {price:,.0f}$

🏦 Mise de fonds : {down:,.0f}$ ({metrics['down_ratio']:.1f}%)

👤 Revenu : {income:,.0f}$/an
""")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

st.subheader("📈 Tendances économiques")

if market == "Québec / Canada":
    hist = get_canada_rate_history()
    st.line_chart(hist.set_index("Date"))
else:
    st.info("Historique US complet à venir. Version actuelle : analyse avec taux de référence estimé.")

st.divider()

st.subheader("🔒 ImmoRadar Premium")

p1, p2, p3 = st.columns(3)

with p1:
    st.markdown("""
<div class="price-card">
<h3>Gratuit</h3>
<h2>0$/mois</h2>
<div class="price-feature">✅ Score immobilier</div>
<div class="price-feature">✅ Analyse simple</div>
<div class="price-feature">✅ Rapport texte</div>
<div class="price-feature">✅ Canada + USA</div>
</div>
""", unsafe_allow_html=True)

with p2:
    st.markdown("""
<div class="price-card">
<h3>Pro</h3>
<h2>19$/mois</h2>
<div class="price-feature">✅ Analyse IA avancée</div>
<div class="price-feature">✅ Alertes marché</div>
<div class="price-feature">✅ Rapports PDF pro</div>
<div class="price-feature">✅ Suivi de villes</div>
</div>
""", unsafe_allow_html=True)

with p3:
    st.markdown("""
<div class="price-card">
<h3>Investisseur</h3>
<h2>49$/mois</h2>
<div class="price-feature">✅ Multi-propriétés</div>
<div class="price-feature">✅ Cashflow avancé</div>
<div class="price-feature">✅ Comparaison de marchés</div>
<div class="price-feature">✅ Export complet</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cta-box">
<h3>📩 Liste d’attente Premium</h3>
<p>Objectif : valider l’intérêt avant de construire le paiement. Partage ce site et demande aux gens s’ils paieraient pour les alertes et rapports avancés.</p>
</div>
""", unsafe_allow_html=True)

st.divider()

st.subheader("📄 Rapport téléchargeable")

report = f"""
RAPPORT IMMRADAR

Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}
Marché : {market}
Ville : {city}
Objectif : {objective}
Type : {property_type}

SCORE
Score ImmoRadar : {score}/100
Statut : {label}

DONNÉES ÉCONOMIQUES
- Taux d’intérêt : {taux}%
- Inflation : {inflation}%
- Chômage : {chomage}%

DONNÉES FINANCIÈRES
- Prix : {price:,.0f}$
- Mise de fonds : {down:,.0f}$
- Mise de fonds (%) : {metrics['down_ratio']:.1f}%
- Revenu annuel : {income:,.0f}$
- Paiement hypothécaire estimé : {metrics['monthly_payment']:,.0f}$/mois
- Ratio paiement/revenu : {metrics['monthly_debt_ratio']*100:.1f}%
- Cashflow estimé : {metrics['net_cashflow']:,.0f}$/mois

ANALYSE
{chr(10).join('- ' + p for p in analysis_points)}

CONCLUSION
{conclusion}

NOTE
Ce rapport est éducatif. Il ne remplace pas un conseil financier, fiscal, hypothécaire, juridique ou immobilier professionnel.
"""

st.download_button(
    "📥 Télécharger le rapport ImmoRadar",
    data=report,
    file_name="rapport_immoradar.txt",
    mime="text/plain"
)

st.markdown("""
<div class="footer">
ImmoRadar — Prototype SaaS immobilier intelligent. Données et résultats à valider avant toute décision financière.
</div>
""", unsafe_allow_html=True)
