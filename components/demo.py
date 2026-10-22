"""Try the real financial engine without signing up or contacting a provider."""
import json
import streamlit as st

from components.sidebar import go_to
from domain.investment_criteria import screen_snapshot
from services.demo_service import demo_inputs, demo_snapshot
from services.report_service import generate_report_pdf


def _money(value):
    return f"{value:,.0f} $".replace(",", " ")


def show_demo():
    st.html("<h1>Essayez Cenlio sur un exemple</h1>")
    st.info("Démonstration fictive : aucune adresse réelle, aucune estimation marchande et aucun résultat garanti. Les calculs utilisent le même moteur que vos dossiers.")
    st.write("Modifiez trois hypothèses et observez leur effet. Aucun compte, aucune recherche publique et aucune sauvegarde de vos choix.")
    price, rent, rate = st.columns(3)
    with price:
        asking = st.slider("Prix retenu ($)", 150_000, 1_000_000, 500_000, 10_000, key="demo_price")
    with rent:
        income = st.slider("Loyers bruts ($/mois)", 0, 10_000, 4_000, 100, key="demo_rent")
    with rate:
        interest = st.slider("Taux hypothécaire (%)", 0.0, 15.0, 5.0, 0.1, key="demo_interest")
    inputs = demo_inputs(float(asking), float(income), float(interest))
    snapshot, financial = demo_snapshot(inputs)
    payment, cash, coverage = st.columns(3)
    payment.metric("Paiement hypothécaire", _money(financial.monthly_payment) + "/mois")
    cash.metric("Flux après dépenses", _money(financial.cash_flow_monthly) + "/mois")
    coverage.metric("Couverture de dette", f"{financial.debt_service_coverage_ratio:.2f}x" if income else "Non applicable")
    st.caption("Mise de fonds fictive : 100 000 $ · Amortissement : 25 ans · Vacance : 3 % des loyers · Dépenses et réserves incluses. La convention hypothécaire canadienne de composition semestrielle est utilisée.")
    with st.expander("Voir toutes les hypothèses de l’exemple"):
        st.dataframe([{"Hypothèse": "Taxes municipales / an", "Montant": "3 600 $"},
                      {"Hypothèse": "Taxes scolaires / an", "Montant": "400 $"},
                      {"Hypothèse": "Assurance / mois", "Montant": "150 $"},
                      {"Hypothèse": "Entretien / mois", "Montant": "150 $"},
                      {"Hypothèse": "Réserve travaux / mois", "Montant": "150 $"},
                      {"Hypothèse": "Autres dépenses / mois", "Montant": "100 $"},
                      {"Hypothèse": "Travaux initiaux", "Montant": "10 000 $"},
                      {"Hypothèse": "Acquisition", "Montant": "10 000 $"}], hide_index=True, width="stretch")
    st.markdown("### La décision change-t-elle dans un scénario prudent ?")
    scenarios = json.loads(snapshot["scenarios_json"])
    st.dataframe([{"Scénario": row["name"], "Flux mensuel": _money(row["financial"]["cash_flow_monthly"]),
                   "Paiement": _money(row["financial"]["monthly_payment"]),
                   "Couverture": f"{row['financial']['debt_service_coverage_ratio']:.2f}x" if income else "Non applicable"} for row in scenarios],
                 hide_index=True, width="stretch")
    st.caption("Prudent : taux +1 point, loyers −5 %, vacance +3 points et dépenses variables +10 %. Favorable : illustration de sensibilité, jamais une prévision.")
    st.markdown("### L’aperçu des critères Premium")
    st.caption(r"Exemple de critères : flux de base ≥ 0 \$/mois, couverture ≥ 1,10x et flux prudent ≥ 0 \$/mois. Dans votre compte Premium, vous choisissez vos propres seuils.")
    result = screen_snapshot(snapshot, {"min_cash_flow": 0, "min_dscr": 1.1, "min_prudent_cash_flow": 0})
    labels = {"matches": "Cet exemple respecte les trois seuils.", "outside": "Cet exemple ne respecte pas tous les seuils.", "incomplete": "Des critères ne sont pas calculables avec ces hypothèses."}
    st.write(labels[result["status"]])
    st.download_button("Voir le rapport PDF de cet exemple", generate_report_pdf(snapshot),
                       "cenlio-demonstration-fictive.pdf", "application/pdf", key="demo_pdf", width="stretch")
    first, second = st.columns(2)
    first.button("Analyser ma propre propriété", type="primary", on_click=go_to, args=("Analyser",), key="demo_start", width="stretch")
    second.button("Découvrir les outils Premium", on_click=go_to, args=("Premium",), key="demo_premium", width="stretch")
