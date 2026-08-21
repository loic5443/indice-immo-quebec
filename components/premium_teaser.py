"""Short, truthful Premium invitations placed at the moment of product value."""

import streamlit as st

from components.sidebar import go_to


def show_premium_teaser(*, feature: str, title: str, detail: str, key: str) -> None:
    """Explain one locked outcome without implying it is already active."""

    st.markdown(
        "<section class='premium-conversion-card'><p class='eyebrow notranslate'>PREMIUM</p>"
        f"<div class='notice-title' role='heading' aria-level='3'>{title}</div>"
        f"<p><b>{feature}</b> — {detail}</p>"
        "<p class='premium-conversion-note'>Aucun paiement n’est demandé pendant la bêta privée.</p></section>",
        unsafe_allow_html=True,
    )
    st.button("Découvrir Premium", on_click=go_to, args=("Premium",), key=key, use_container_width=True)
