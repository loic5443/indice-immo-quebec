import streamlit as st


def show_premium(score, ville, prix, mise, revenu, taux, inflation, chomage):
    st.title("ImmoRadar Premium")
    st.write("Des outils approfondis pour comparer un projet et documenter vos hypothèses.")
    st.warning("Version de présentation : aucun paiement, abonnement ou accès Premium réel n'est activé.")

    starter, premium = st.columns(2)
    with starter:
        st.subheader("Essentiel — gratuit")
        st.write("✓ Score de contexte\n✓ Simulation de budget\n✓ Rapport téléchargeable\n✓ Données d'exemple identifiées")
    with premium:
        st.subheader("Premium — à venir")
        st.write("✓ Prévision sur 12 mois\n✓ Score investisseur\n✓ Calculateur locatif\n✓ Analyse détaillée")
        st.button("Être informé du lancement", disabled=True, help="Les abonnements ne sont pas encore ouverts.")

    st.divider()
    tab1, tab2, tab3, tab4 = st.tabs(["Prévision", "Score investisseur", "Locatif", "Analyse avancée"])
    with tab1:
        variation = "+1 % à +2 %" if taux >= 5 else "+3 % à +6 %" if inflation <= 3 and chomage < 6 else "+2 % à +3 %"
        st.info(f"Pour {ville}, la projection illustrative est de {variation} sur 12 mois.")
        st.caption("Projection d'exemple basée sur les variables saisies; ce n'est pas une prévision de marché réelle.")
    with tab2:
        ratio_mise, ratio_prix_revenu = mise / prix * 100, prix / revenu
        score_investisseur = 100 - (20 if taux > 5 else 0) - (10 if inflation > 3 else 0) - (10 if chomage > 6 else 0) - (15 if ratio_mise < 10 else 0) - (20 if ratio_prix_revenu > 6 else 0)
        score_investisseur = max(0, min(100, round(score_investisseur)))
        st.metric("Score investisseur indicatif", f"{score_investisseur}/100")
        st.caption("Calcul éducatif, à compléter par une analyse financière professionnelle.")
    with tab3:
        revenu_locatif = st.number_input("Revenus locatifs mensuels ($)", min_value=0, value=2200, step=100)
        depenses = st.number_input("Dépenses mensuelles ($)", min_value=0, value=900, step=50)
        hypotheque = st.number_input("Paiement hypothécaire mensuel ($)", min_value=0, value=1800, step=50)
        cashflow = revenu_locatif - depenses - hypotheque
        rendement = revenu_locatif * 12 / prix * 100
        one, two = st.columns(2)
        one.metric("Flux mensuel indicatif", f"{cashflow:,} $")
        two.metric("Rendement brut indicatif", f"{rendement:.2f} %")
    with tab4:
        st.write(f"Score de contexte actuel : **{score}/100**.")
        st.write("Les conclusions sont générées à partir des hypothèses affichées et doivent être validées avant une décision.")
