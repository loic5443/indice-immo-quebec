import streamlit as st

def show_premium():

    st.markdown("""
    ## 🚀 ImmoRadar Premium

    Débloquez une analyse immobilière avancée avec alertes intelligentes et données économiques détaillées.
    """)

    premium1, premium2, premium3 = st.columns(3)

    with premium1:
        st.markdown("""
        <div style="background-color:#111827; padding:25px; border-radius:18px; border:1px solid #334155;">
            <h3>📩 Alertes intelligentes</h3>
            <p>Recevez une alerte quand le marché devient favorable.</p>
        </div>
        """, unsafe_allow_html=True)

    with premium2:
        st.markdown("""
        <div style="background-color:#111827; padding:25px; border-radius:18px; border:1px solid #334155;">
            <h3>🤖 Analyse IA avancée</h3>
            <p>Analyse personnalisée selon votre budget et votre ville.</p>
        </div>
        """, unsafe_allow_html=True)

    with premium3:
        st.markdown("""
        <div style="background-color:#111827; padding:25px; border-radius:18px; border:1px solid #334155;">
            <h3>📈 Historique complet</h3>
            <p>Suivez les tendances immobilières et économiques.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    st.button("🔥 Passer au Premium")