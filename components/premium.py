import streamlit as st


def show_premium(score, ville, prix, mise, revenu, taux, inflation, chomage):

    st.markdown("""
    ## 🚀 ImmoRadar Premium

    Débloquez les outils avancés pour analyser une ville, prévoir le marché et évaluer un investissement immobilier.
    """)

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "📈 Prévision 12 mois",
        "🏘️ Score investisseur",
        "💰 Investissement locatif",
        "🤖 Analyse IA avancée"
    ])

    with onglet1:

        st.subheader("📈 Prévision immobilière sur 12 mois")

        if taux >= 5:
            prevision = "croissance faible ou ralentissement"
            variation = "+1% à +2%"

        elif inflation <= 3 and chomage < 6:
            prevision = "croissance favorable"
            variation = "+3% à +6%"

        else:
            prevision = "marché stable"
            variation = "+2% à +3%"

        st.info(f"""
Pour {ville} :

- Tendance probable : {prevision}
- Variation estimée : {variation}
- Analyse basée sur les taux, inflation et chômage.
""")

    with onglet2:

        st.subheader("🏘️ Score investisseur avancé")

        ratio_mise = (mise / prix) * 100
        ratio_prix_revenu = prix / revenu

        score_investisseur = 100

        if taux > 5:
            score_investisseur -= 20

        if inflation > 3:
            score_investisseur -= 10

        if chomage > 6:
            score_investisseur -= 10

        if ratio_mise < 10:
            score_investisseur -= 15

        if ratio_prix_revenu > 6:
            score_investisseur -= 20

        score_investisseur = max(
            0,
            min(100, round(score_investisseur))
        )

        st.metric(
            "Score investisseur",
            f"{score_investisseur}/100"
        )

        if score_investisseur >= 75:

            st.success(
                "Excellent potentiel d’investissement."
            )

        elif score_investisseur >= 50:

            st.warning(
                "Potentiel moyen. Analyse plus poussée recommandée."
            )

        else:

            st.error(
                "Projet risqué selon les données actuelles."
            )

    with onglet3:

        st.subheader("💰 Calculateur investissement locatif")

        revenu_locatif = st.number_input(
            "Revenus locatifs mensuels ($)",
            value=2200,
            step=100
        )

        depenses = st.number_input(
            "Dépenses mensuelles ($)",
            value=900,
            step=50
        )

        hypotheque = st.number_input(
            "Paiement hypothécaire mensuel ($)",
            value=1800,
            step=50
        )

        cashflow = revenu_locatif - depenses - hypotheque

        rendement = (
            (revenu_locatif * 12) / prix
        ) * 100

        col1, col2 = st.columns(2)

        col1.metric(
            "💵 Cashflow mensuel",
            f"{cashflow:,}$"
        )

        col2.metric(
            "📈 Rendement brut",
            f"{round(rendement, 2)}%"
        )

        if cashflow > 0:

            st.success(
                "Le projet semble générer un cashflow positif."
            )

        else:

            st.warning(
                "Le projet semble générer un cashflow négatif."
            )

        if rendement >= 8:

            st.success(
                "Excellent rendement locatif."
            )

        elif rendement >= 5:

            st.info(
                "Rendement correct selon le marché actuel."
            )

        else:

            st.error(
                "Rendement relativement faible."
            )

    with onglet4:

        st.subheader("🤖 Analyse IA avancée")

        analyse_premium = []

        if score >= 75:

            analyse_premium.append(
                "Le marché semble favorable actuellement."
            )

        elif score >= 50:

            analyse_premium.append(
                "Le marché demande de la prudence."
            )

        else:

            analyse_premium.append(
                "Le marché semble risqué actuellement."
            )

        if taux >= 5:

            analyse_premium.append(
                "Les taux élevés réduisent la capacité d’achat."
            )

        else:

            analyse_premium.append(
                "Les taux sont relativement favorables."
            )

        if mise / prix >= 0.20:

            analyse_premium.append(
                "La mise de fonds réduit le risque financier."
            )

        else:

            analyse_premium.append(
                "Une mise de fonds plus élevée serait préférable."
            )

        for point in analyse_premium:

            st.write("• " + point)

        if st.button("🔥 Activer Premium"):

            st.session_state["premium"] = True
