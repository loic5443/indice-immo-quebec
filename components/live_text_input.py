"""A small live text field that sends input changes to Streamlit reliably."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


_component = components.declare_component(
    "immoradar_live_text_input",
    path=str(Path(__file__).with_name("live_text_input_frontend")),
)


def live_text_input(
    label: str,
    *,
    value: str = "",
    placeholder: str = "",
    debounce_ms: int = 400,
    key: str,
) -> str:
    """Return a debounced value on each real input or keyup event.

    The frontend is an ordinary text input: it deliberately has no option
    list, combobox role, or selection behaviour. Suggestions stay in the
    parent Streamlit page where they can be rendered once and selected safely.
    """

    result = _component(
        label=label,
        value=value,
        placeholder=placeholder,
        debounce_ms=debounce_ms,
        key=key,
        default=value,
    )
    return result if isinstance(result, str) else value
