"""Short, truthful Premium invitations placed at the moment of product value."""

import os

import streamlit as st

from components.sidebar import go_to


def show_premium_teaser(*, feature: str, title: str, detail: str, key: str) -> None:
    """Explain one locked outcome without implying it is already active."""

    note = ("Consultez le tarif et les conditions dans Premium." if os.environ.get("IMMORADAR_BILLING_ENABLED") == "1"
            else "Aucun paiement n’est demandé pendant la bêta privée.")
    st.markdown(
        "<section class='premium-conversion-card'><p class='eyebrow notranslate'>PREMIUM</p>"
        f"<div class='notice-title' role='heading' aria-level='3'>{title}</div>"
        f"<p><b>{feature}</b> — {detail}</p>"
        f"<p class='premium-conversion-note'>{note}</p></section>",
        unsafe_allow_html=True,
    )
    st.button("Découvrir Premium", on_click=go_to, args=("Premium",), key=key, width="stretch")
