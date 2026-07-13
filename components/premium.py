import streamlit as st


def show_premium() -> None:
    st.title("ImmoRadar Premium")
    st.write("Les outils de base, dont l'analyse immobilière complète, sont disponibles sans abonnement pendant cette phase.")
    st.warning("Aucun paiement, abonnement réel, Stripe ou compte utilisateur n'est activé.")

    free, future = st.columns(2)
    with free:
        st.subheader("Disponible maintenant")
        st.write("✓ Analyse de financement\n✓ Flux de trésorerie\n✓ Rendement sur la mise\n✓ Taux de capitalisation\n✓ Ratio de couverture de la dette")
    with future:
        st.subheader("Fonctions Premium à venir")
        st.write("• Comparaison de scénarios\n• Rapports exportables\n• Alertes de marché enrichies\n• Suivi multi-propriétés")
        st.button("Être informé du lancement", disabled=True)
