"""Complete property analysis UI with enriched assumptions and deterministic scenarios."""

from dataclasses import asdict
import re
import unicodedata

import streamlit as st
from streamlit_searchbox import st_searchbox

from calculations.real_estate import AnalysisResult, PropertyInputs, calculate_analysis, validate_inputs
from components.account import current_user, is_authenticated
from components.immoengine import show_immoengine_result
from components.scenarios import show_scenarios
from components.sidebar import go_to
from data.database import save_analysis
from data.database import DATABASE_PATH
from domain.immoengine import PROFILE_WEIGHTS, evaluate_immoengine
from services.market_data_service import market_context_snapshot
from domain.immovalue import SubjectProperty, estimate_immovalue
from services.comparable_csv import csv_template, validate_csv_rows
from services.analysis_workflow import STEPS, load_draft, save_draft, normalize_step, transition
from services.entitlements_service import quota_status, consume_estimation
from services.address_lookup_service import lookup
from services.quebec_role_importer import search_role_units,role_street_variants,suggest_role_units
from services.quebec_role_admin_service import territory_for_municipality
from services.address_form_service import (
    AddressFormState,
    empty_address_form_state,
    restore_address_form,
    serialize_address_form,
    submit_address_form,
)
from services.quebec_address_geocoder import (
    SOURCE_ID,
    SOURCE_LABEL,
    SuggestionResponse,
    AddressSuggestion,
    resolve_suggestion,
    resolve_freeform_address,
    suggest_addresses,
    useful_query,
)
from domain.address import normalize_canadian_postal_code
from services.diagnostics_service import source_enabled


DEFAULTS = {
    "property_price": 0.0, "down_payment": 0.0, "mortgage_rate": 0.0,
    "amortization_years": 25, "municipal_taxes": 0.0, "school_taxes": 0.0,
    "insurance": 0.0, "condo_fees": 0.0, "rental_income": 0.0,
    "other_expenses": 0.0, "household_income": 0.0, "other_debts": 0.0,
    "vacancy_rate": 0.0, "maintenance": 0.0, "management": 0.0,
    "utilities": 0.0, "capital_reserve": 0.0, "initial_repairs": 0.0,
    "acquisition_costs": 0.0, "other_income": 0.0, "rent_growth": 0.0,
    "expense_growth": 0.0, "holding_period": 5,
}

ANALYSIS_OBJECTIVES = {
    "Acheter pour y habiter": "Premier acheteur",
    "Investir et louer": "Investisseur locatif",
    "Connaître la valeur de ma propriété": "Propriétaire",
    "Préparer une vente": "Propriétaire",
}

ADDRESS_STATE_KEY = "address_form_state"
ADDRESS_LOOKUP_KEY = "address_form_lookup"
ADDRESS_OWNER_KEY = "address_form_owner"
ADDRESS_HYDRATE_KEY = "address_form_hydrate"
ADDRESS_SUGGESTIONS_KEY = "address_form_suggestions"
ADDRESS_SUGGESTION_QUERY_KEY = "address_form_suggestion_query"
ADDRESS_AUTOCOMPLETE_KEY = "address_form_autocomplete"
ADDRESS_EDITOR_STREET_KEY = "address_form_editor_street"
ADDRESS_MANUAL_MODE_KEY = "address_form_manual_mode"
ADDRESS_RESOLUTION_KEY = "address_form_resolution"
ADDRESS_RESOLUTION_SELECTION_KEY = "address_form_resolution_selection"
ADDRESS_LOCAL_SELECTED_KEY = "address_form_local_selected"
ADDRESS_WIDGET_KEYS = {
    "street": "address_form_street",
    "city": "address_form_city",
    "postal": "address_form_postal",
    "unit": "address_form_unit",
    "consent": "address_form_consent",
}


def reset_analysis() -> None:
    st.session_state.update(DEFAULTS)
    st.session_state.pop("analysis_calculation_signature", None)
    st.session_state.pop("analysis_calculation_requested", None)
    st.session_state.pop("analysis_calculation_errors", None)


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def prepare_address_submission(street: str, city: str, postal: str, unit: str = "", consent: bool = False) -> AddressFormState:
    """Compatibility entry point used by UI tests and the submitted form."""
    return submit_address_form(street, city, postal, unit, consent)


def _address_owner_id() -> int | None:
    return current_user()["id"] if is_authenticated() else None


def _hydrate_address_widgets(state: AddressFormState) -> None:
    """Synchronize widget editors before they are instantiated in this rerun."""
    for field, key in ADDRESS_WIDGET_KEYS.items():
        if field != "street":
            st.session_state[key] = state.values[field]
    st.session_state[ADDRESS_EDITOR_STREET_KEY] = state.values["street"]
    # The search component owns its own frontend state. Reset it only before
    # rendering, so a selected address and the visible editor never diverge.
    st.session_state.pop(ADDRESS_AUTOCOMPLETE_KEY, None)


def _address_state_for_current_user() -> AddressFormState:
    """Load exactly one canonical state for the active user/session."""
    owner_id = _address_owner_id()
    # Anonymous sessions use ``None`` as their owner id.  Test key presence,
    # not only equality, or a fresh anonymous session would skip its first
    # canonical hydration (including the Accueil → Analyser hand-off).
    if ADDRESS_OWNER_KEY not in st.session_state or st.session_state.get(ADDRESS_OWNER_KEY) != owner_id:
        state = empty_address_form_state()
        restored_draft = False
        if owner_id is not None:
            draft, _ = load_draft(owner_id, DATABASE_PATH)
            restored_draft = bool(draft.get("address_form"))
            state = restore_address_form(draft.get("address_form"))
        # Preserve values entered in the first browser event before the
        # canonical state has been initialized.  This also prevents a rerun
        # from turning an already selected manual mode or consent back off.
        if not restored_draft:
            values = dict(state.values)
            for field, key in ADDRESS_WIDGET_KEYS.items():
                if key in st.session_state:
                    values[field] = st.session_state[key]
            if ADDRESS_EDITOR_STREET_KEY in st.session_state:
                values["street"] = st.session_state[ADDRESS_EDITOR_STREET_KEY]
            state = AddressFormState(values=values, address=None, errors={})
        st.session_state[ADDRESS_OWNER_KEY] = owner_id
        st.session_state[ADDRESS_STATE_KEY] = state
        st.session_state[ADDRESS_HYDRATE_KEY] = True
        st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
        _clear_address_suggestions()
    state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
    # The Accueil hand-off must work even when this anonymous session already
    # visited Analyser.  It is therefore applied independently of owner/draft
    # initialization and forces a fresh searchbox iframe value on this rerun.
    home_address = useful_query(st.session_state.pop("home_address_pending", ""))
    if home_address:
        values = dict(state.values)
        values["street"] = home_address
        state = AddressFormState(values=values, address=None, errors={})
        st.session_state[ADDRESS_STATE_KEY] = state
        st.session_state[ADDRESS_HYDRATE_KEY] = True
        st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
        _clear_address_suggestions()
    if st.session_state.pop(ADDRESS_HYDRATE_KEY, False):
        _hydrate_address_widgets(state)
    return state


def _persist_address_draft(state: AddressFormState) -> None:
    """Save the JSON-safe canonical submission only in the signed-in user's draft."""
    owner_id = _address_owner_id()
    if owner_id is None:
        return
    draft, step = load_draft(owner_id, DATABASE_PATH)
    draft["address_form"] = serialize_address_form(state)
    save_draft(owner_id, draft, step, DATABASE_PATH)


def _clear_address_suggestions() -> None:
    """Suggestions are ephemeral: they are never saved in drafts or telemetry."""

    st.session_state.pop(ADDRESS_SUGGESTIONS_KEY, None)
    st.session_state.pop(ADDRESS_SUGGESTION_QUERY_KEY, None)


def _edit_address_field(field: str) -> None:
    """Invalidate only an edited canonical submission before the next confirmation."""

    state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
    values = dict(state.values)
    value = st.session_state.get(ADDRESS_WIDGET_KEYS[field], "")
    if field == "postal" and value:
        normalized = normalize_canadian_postal_code(value)
        if normalized:
            value = normalized
            st.session_state[ADDRESS_WIDGET_KEYS[field]] = normalized
    values[field] = value
    errors = {name: message for name, message in state.errors.items() if name != field}
    st.session_state[ADDRESS_STATE_KEY] = AddressFormState(values=values, address=None, errors=errors)
    st.session_state.pop(ADDRESS_LOOKUP_KEY, None)


def _set_address_editor_street(value: str) -> None:
    """Keep the transient editor in sync without saving a draft prematurely."""

    state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
    values = dict(state.values)
    values["street"] = value
    errors = {name: message for name, message in state.errors.items() if name != "street"}
    st.session_state[ADDRESS_EDITOR_STREET_KEY] = value
    st.session_state[ADDRESS_STATE_KEY] = AddressFormState(values=values, address=None, errors=errors)
    st.session_state.pop(ADDRESS_LOOKUP_KEY, None)


def _autocomplete_options(query: str) -> list[tuple[str, dict[str, str]]]:
    """Return live MRNF options after debounce; never transmit without consent."""

    query = useful_query(query)
    _set_address_editor_street(query)
    consent = bool(st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False))
    if not consent or st.session_state.get(ADDRESS_MANUAL_MODE_KEY, False):
        _clear_address_suggestions()
        return []

    try:
        enabled = source_enabled(SOURCE_ID, DATABASE_PATH)
    except Exception:
        # A local diagnostic-store problem must never prevent manual analysis
        # and must not generate an address-bearing diagnostic.
        enabled = False
    external = (
        suggest_addresses(query, True)
        if enabled else SuggestionResponse("unavailable", message="La source publique d’adresses est désactivée.")
    )
    local = [
        AddressSuggestion(
            street=row["street"], city=row["city"], postal_code=row["postal_code"],
            unit=row["unit"], label=" · ".join(part for part in (row["street"], row["city"]) if part), source="role",
        )
        for row in suggest_role_units(DATABASE_PATH, query, limit=8)
    ]
    combined = _merge_address_suggestions(external.suggestions, local)
    if combined:
        response = SuggestionResponse("ok", tuple(combined))
    elif external.status == "ok":
        response = SuggestionResponse("ok", message="Aucune adresse publique ne correspond. Vous pouvez poursuivre en mode manuel.")
    else:
        response = external
    st.session_state[ADDRESS_SUGGESTIONS_KEY] = response
    st.session_state[ADDRESS_SUGGESTION_QUERY_KEY] = query
    if response.status != "ok" or not response.suggestions:
        # streamlit-searchbox has no translation hook for “No options”.  A
        # non-selectable status item keeps its listbox clear and French.
        return [(response.message or "Aucune adresse publique ne correspond. Vous pouvez poursuivre en mode manuel.", {"source": "empty", "label": response.message})]
    return [(suggestion.label, suggestion.to_option()) for suggestion in response.suggestions]


def _suggestion_key(suggestion: AddressSuggestion) -> str:
    value = re.sub(r"\b[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ]\s?\d[ABCEGHJKLMNPRSTVWXYZ]\d\b", "", suggestion.label, flags=re.I)
    value = "".join(char for char in unicodedata.normalize("NFD", value.casefold()) if not unicodedata.combining(char))
    return "".join(char for char in value if char.isalnum())


def _merge_address_suggestions(external: tuple[AddressSuggestion, ...], local: list[AddressSuggestion]) -> list[AddressSuggestion]:
    """Keep external results first while deduplicating a bounded local fallback."""

    merged: list[AddressSuggestion] = []
    seen: set[str] = set()
    for suggestion in (*external, *local):
        key = _suggestion_key(suggestion)
        if key and key not in seen:
            seen.add(key)
            merged.append(suggestion)
        if len(merged) >= 8:
            break
    return merged


def _on_address_city_change() -> None:
    _edit_address_field("city")
    _clear_address_suggestions()


def _on_address_postal_change() -> None:
    _edit_address_field("postal")


def _on_address_unit_change() -> None:
    _edit_address_field("unit")


def _on_address_consent_change() -> None:
    _edit_address_field("consent")
    if not st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False):
        _clear_address_suggestions()


def _on_manual_mode_change() -> None:
    """Changing mode is local-only and clears ephemeral external suggestions."""

    _clear_address_suggestions()


def _select_address_suggestion(suggestion: dict[str, str]) -> None:
    """Fill visible editors together; final saving still needs the normal confirmation."""

    selected = AddressSuggestion(
        street=suggestion.get("street", ""),
        city=suggestion.get("city", ""),
        postal_code=suggestion.get("postal_code", ""),
        unit=suggestion.get("unit", ""),
        label=suggestion.get("label", ""),
        lookup_key=suggestion.get("lookup_key", ""),
        source=suggestion.get("source", "external"),
    )
    if selected.source == "empty":
        return
    # The official endpoint resolves the opaque selection key to structured
    # fields only after a person clicks it.  The key stays session-only.
    resolved = selected if selected.source == "role" else resolve_suggestion(selected, bool(st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False)))
    if resolved is None:
        _clear_address_suggestions()
        st.session_state[ADDRESS_SUGGESTIONS_KEY] = SuggestionResponse(
            "unavailable",
            message="La suggestion ne peut pas être complétée pour le moment. Vous pouvez saisir l’adresse manuellement.",
        )
        return

    state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
    values = dict(state.values)
    values.update(
        {
            "street": resolved.street,
            "city": resolved.city or values.get("city", ""),
            "postal": resolved.postal_code or values.get("postal", ""),
            "unit": resolved.unit or values.get("unit", ""),
            "consent": bool(st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False)),
        }
    )
    st.session_state[ADDRESS_STATE_KEY] = AddressFormState(values=values, address=None, errors={})
    st.session_state[ADDRESS_EDITOR_STREET_KEY] = resolved.street
    # This callback runs before the adjacent editors are instantiated in the
    # same rerun, so they can safely receive the selected canonical values.
    st.session_state[ADDRESS_WIDGET_KEYS["city"]] = values["city"]
    st.session_state[ADDRESS_WIDGET_KEYS["postal"]] = values["postal"]
    st.session_state[ADDRESS_WIDGET_KEYS["unit"]] = values["unit"]
    st.session_state[ADDRESS_HYDRATE_KEY] = True
    st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
    if selected.source == "role":
        st.session_state[ADDRESS_LOCAL_SELECTED_KEY] = True
        st.session_state[ADDRESS_LOOKUP_KEY] = _official_lookup_fields(values["street"], values["city"], True, postal_available=False)
    else:
        st.session_state.pop(ADDRESS_LOCAL_SELECTED_KEY, None)
    _clear_address_suggestions()


def _select_resolved_address() -> None:
    """Apply an explicitly selected candidate from the consented resolution."""

    response = st.session_state.get(ADDRESS_RESOLUTION_KEY)
    index = st.session_state.get(ADDRESS_RESOLUTION_SELECTION_KEY)
    if not isinstance(response, SuggestionResponse) or not isinstance(index, int):
        return
    if index < 0 or index >= len(response.suggestions):
        return
    candidate = response.suggestions[index]
    state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
    values = dict(state.values)
    values.update({
        "street": candidate.street or values["street"],
        "city": candidate.city or values["city"],
        "postal": candidate.postal_code or values["postal"],
    })
    st.session_state[ADDRESS_STATE_KEY] = AddressFormState(values=values, address=None, errors={})
    st.session_state[ADDRESS_HYDRATE_KEY] = True
    st.session_state[ADDRESS_EDITOR_STREET_KEY] = values["street"]
    st.session_state[ADDRESS_WIDGET_KEYS["city"]] = values["city"]
    st.session_state[ADDRESS_WIDGET_KEYS["postal"]] = values["postal"]


def _submit_address_lookup() -> None:
    """Validate and persist the exact same widget values in one explicit action."""
    street = st.session_state.get(ADDRESS_EDITOR_STREET_KEY, st.session_state.get(ADDRESS_WIDGET_KEYS["street"], ""))
    city = st.session_state.get(ADDRESS_WIDGET_KEYS["city"], "")
    postal = st.session_state.get(ADDRESS_WIDGET_KEYS["postal"], "")
    consent = bool(st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False))
    st.session_state.pop(ADDRESS_RESOLUTION_KEY, None)
    # A copied address from Accueil often has no separate city/postal fields.
    # Resolve it only here, after an explicit consented action; ambiguity is
    # left to the person instead of guessing a municipality or unit.
    if consent and street and (not city or not postal):
        try:
            geocoder_enabled = source_enabled(SOURCE_ID, DATABASE_PATH)
        except Exception:
            geocoder_enabled = False
        resolution = (
            resolve_freeform_address(street, True)
            if geocoder_enabled
            else SuggestionResponse("unavailable", message="La source publique d’adresses est désactivée. Vous pouvez poursuivre en mode manuel.")
        )
        st.session_state[ADDRESS_RESOLUTION_KEY] = resolution
        if resolution.status == "ok" and len(resolution.suggestions) == 1:
            candidate = resolution.suggestions[0]
            street = candidate.street or street
            city = candidate.city or city
            postal = candidate.postal_code or postal
            st.session_state[ADDRESS_EDITOR_STREET_KEY] = street
            st.session_state[ADDRESS_WIDGET_KEYS["city"]] = city
            st.session_state[ADDRESS_WIDGET_KEYS["postal"]] = postal
    state = prepare_address_submission(
        street,
        city,
        postal,
        st.session_state.get(ADDRESS_WIDGET_KEYS["unit"], ""),
        consent,
    )
    st.session_state[ADDRESS_STATE_KEY] = state
    _persist_address_draft(state)
    if state.valid:
        st.session_state[ADDRESS_LOOKUP_KEY] = _official_lookup(state)
    else:
        st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
    st.session_state[ADDRESS_HYDRATE_KEY] = True
    _clear_address_suggestions()


def _official_lookup(state: AddressFormState) -> dict:
    """Use the same canonical address for consent and the local official lookup."""
    assert state.address is not None
    result = lookup(state.address, state.values["consent"])
    response = _official_lookup_fields(state.address.street, state.address.city, state.values["consent"])
    response["message"] = result["message"]
    response["normalized_address"] = {
        "street": state.address.street, "city": state.address.city,
        "postal": state.address.postal_code, "unit": state.address.unit,
    }
    return response


def _official_lookup_fields(street: str, city: str, consent: bool, *, postal_available: bool = True) -> dict:
    """Match public role fields without treating municipal data as an estimate."""

    response = {
        "message": "Renseignements publics recherchés.", "consent": consent,
        "coverage": None, "territory": None, "matches": [], "variants": [],
        "normalized_address": {"street": street, "city": city, "postal": "", "unit": ""},
        "postal_available": postal_available,
    }
    if not consent:
        return response
    territory = territory_for_municipality(DATABASE_PATH, city)
    matches = search_role_units(DATABASE_PATH, territory, street) if territory else []
    response.update({
        "coverage": bool(territory),
        "territory": territory,
        "matches": matches,
        "variants": role_street_variants(DATABASE_PATH, territory, street) if territory and not matches else [],
    })
    return response


def _inputs_from_state() -> PropertyInputs:
    household_income = st.session_state["household_income"] or None
    return PropertyInputs(
        price=st.session_state["property_price"], down_payment=st.session_state["down_payment"],
        annual_interest_rate=st.session_state["mortgage_rate"], amortization_years=st.session_state["amortization_years"],
        municipal_taxes_annual=st.session_state["municipal_taxes"], school_taxes_annual=st.session_state["school_taxes"],
        insurance_monthly=st.session_state["insurance"], condo_fees_monthly=st.session_state["condo_fees"],
        rental_income_monthly=st.session_state["rental_income"], other_expenses_monthly=st.session_state["other_expenses"],
        household_income_annual=household_income, other_debt_payments_monthly=st.session_state["other_debts"],
        vacancy_rate_pct=st.session_state["vacancy_rate"], maintenance_monthly=st.session_state["maintenance"],
        management_monthly=st.session_state["management"], owner_paid_utilities_monthly=st.session_state["utilities"],
        capital_reserve_monthly=st.session_state["capital_reserve"], initial_repairs=st.session_state["initial_repairs"],
        acquisition_costs=st.session_state["acquisition_costs"], other_income_monthly=st.session_state["other_income"],
        rent_growth_annual_pct=st.session_state["rent_growth"], expense_growth_annual_pct=st.session_state["expense_growth"],
        holding_period_years=st.session_state["holding_period"],
    )


def _analysis_signature(inputs: PropertyInputs) -> tuple:
    """A result is displayed only for the exact values explicitly calculated."""
    return tuple(asdict(inputs).items())


def _workflow_values() -> dict:
    return {
        "profile": st.session_state.get("workflow_profile", ""),
        "objective": st.session_state.get("workflow_objective", ""),
        "property_name": st.session_state.get("workflow_property_name", ""),
        "property_type": st.session_state.get("workflow_property_type", ""),
        "price": st.session_state.get("property_price", 0),
        "down_payment": st.session_state.get("down_payment", 0),
    }


def _persist_workflow(step: int, completed: set[int]) -> None:
    if not is_authenticated():
        return
    owner_id = current_user()["id"]
    draft, _ = load_draft(owner_id, DATABASE_PATH)
    draft["workflow_completed"] = sorted(completed)
    save_draft(owner_id, draft, step, DATABASE_PATH)


def _ensure_workflow_state() -> tuple[int, set[int]]:
    """Hydrate UI, progress and local draft from one canonical step number."""
    owner_id = _address_owner_id()
    if st.session_state.get("workflow_owner") != owner_id:
        draft, saved_step = load_draft(owner_id, DATABASE_PATH) if owner_id is not None else ({}, 1)
        st.session_state["workflow_owner"] = owner_id
        st.session_state["analysis_step"] = normalize_step(saved_step)
        st.session_state["analysis_completed_steps"] = set(draft.get("workflow_completed", [1])) or {1}
        st.session_state["workflow_errors"] = []
    step = normalize_step(st.session_state.get("analysis_step", 1))
    completed = {normalize_step(item) for item in st.session_state.get("analysis_completed_steps", {1})} or {1}
    st.session_state["analysis_step"] = step
    st.session_state["analysis_completed_steps"] = completed
    st.session_state["analysis_step_selector"] = step
    default_profile = current_user()["user_type"] if is_authenticated() else "Investisseur locatif"
    st.session_state.setdefault("workflow_profile", default_profile)
    st.session_state.setdefault("workflow_objective", "")
    st.session_state.setdefault("workflow_property_name", "")
    st.session_state.setdefault("workflow_property_type", "")
    return step, completed


def _move_workflow(target: int) -> None:
    state = transition(
        st.session_state.get("analysis_step", 1), target,
        st.session_state.get("analysis_completed_steps", {1}), _workflow_values(),
    )
    st.session_state["analysis_step"] = state["step"]
    st.session_state["analysis_completed_steps"] = state["completed"]
    st.session_state["analysis_step_selector"] = state["step"]
    st.session_state["workflow_errors"] = state["errors"]
    _persist_workflow(state["step"], state["completed"])


def _choose_workflow_step() -> None:
    _move_workflow(st.session_state.get("analysis_step_selector", 1))


def _previous_workflow_step() -> None:
    _move_workflow(st.session_state.get("analysis_step", 1) - 1)


def _next_workflow_step() -> None:
    _move_workflow(st.session_state.get("analysis_step", 1) + 1)


def show_property_analysis() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.markdown("<p class='eyebrow'>DOSSIER IMMOBILIER 360</p>", unsafe_allow_html=True)
    st.title("Révéler la valeur et analyser votre projet")
    st.markdown("<p class='section-intro'>Adresse, renseignements publics autorisés, valeur disponible, finances et suivi : un seul dossier, sans transformer les données manquantes en conclusions.</p>", unsafe_allow_html=True)
    address_state = _address_state_for_current_user()
    with st.expander("Commencer par une adresse", expanded=True):
        st.checkbox(
            "J’accepte qu’ImmoRadar recherche des renseignements publics autorisés pour cette adresse.",
            key=ADDRESS_WIDGET_KEYS["consent"],
            on_change=_on_address_consent_change,
        )
        st.checkbox(
            "Saisir manuellement (ne pas rechercher d’adresse)",
            key=ADDRESS_MANUAL_MODE_KEY,
            on_change=_on_manual_mode_change,
        )
        street, city, postal, unit = st.columns(4)
        with street:
            st_searchbox(
                _autocomplete_options,
                label="Adresse",
                placeholder="Ex. 123 rue Exemple",
                default=address_state.values["street"] or None,
                default_searchterm=address_state.values["street"],
                default_use_searchterm=True,
                clear_on_submit=False,
                edit_after_submit="option",
                debounce=400,
                key=ADDRESS_AUTOCOMPLETE_KEY,
                submit_function=_select_address_suggestion,
            )
            if "street" in address_state.errors:
                st.error(address_state.errors["street"])
        with city:
            st.text_input("Ville", key=ADDRESS_WIDGET_KEYS["city"], on_change=_on_address_city_change)
            if "city" in address_state.errors:
                st.error(address_state.errors["city"])
        with postal:
            st.text_input("Code postal", key=ADDRESS_WIDGET_KEYS["postal"], on_change=_on_address_postal_change)
            if "postal" in address_state.errors:
                st.error(address_state.errors["postal"])
        with unit:
            st.text_input("Appartement / local (facultatif)", key=ADDRESS_WIDGET_KEYS["unit"], on_change=_on_address_unit_change)
            if "unit" in address_state.errors:
                st.error(address_state.errors["unit"])
        if not st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False):
            st.caption("Activez le consentement de recherche publique pour obtenir des suggestions d’adresse. La saisie manuelle reste disponible.")
        elif st.session_state.get(ADDRESS_MANUAL_MODE_KEY, False):
            st.caption("Mode manuel actif : aucune recherche externe n’est effectuée.")
        else:
            st.caption("Les suggestions apparaissent automatiquement pendant la saisie.")
        resolution = st.session_state.get(ADDRESS_RESOLUTION_KEY)
        if isinstance(resolution, SuggestionResponse):
            if resolution.status == "ok" and len(resolution.suggestions) > 1:
                st.selectbox(
                    "Plusieurs adresses publiques correspondent : choisissez celle à utiliser",
                    range(len(resolution.suggestions)),
                    key=ADDRESS_RESOLUTION_SELECTION_KEY,
                    format_func=lambda index: resolution.suggestions[index].label,
                    on_change=_select_resolved_address,
                )
            elif resolution.status == "ok" and not resolution.suggestions:
                st.info("Aucune adresse publique correspondante n’a été trouvée. Vérifiez l’adresse ou poursuivez en mode manuel.")
            elif resolution.status in {"unavailable", "rate_limited", "too_short"}:
                st.info(resolution.message)
        suggestion_response = st.session_state.get(ADDRESS_SUGGESTIONS_KEY)
        current_query = useful_query(st.session_state.get(ADDRESS_EDITOR_STREET_KEY, ""))
        if suggestion_response and st.session_state.get(ADDRESS_SUGGESTION_QUERY_KEY) == current_query:
            if suggestion_response.status == "ok" and not suggestion_response.suggestions and len(current_query) >= 3:
                st.info("Aucune suggestion trouvée. Vous pouvez poursuivre avec la saisie manuelle.")
            elif suggestion_response.status in {"unavailable", "rate_limited"}:
                st.info(suggestion_response.message)
            elif suggestion_response.status == "too_short":
                st.caption("Saisissez au moins trois caractères utiles.")
            elif suggestion_response.status == "ok" and suggestion_response.suggestions:
                sources = {suggestion.source for suggestion in suggestion_response.suggestions}
                if sources == {"role"}:
                    st.caption("Source : rôles municipaux officiels synchronisés · résultats publics, non enregistrés automatiquement.")
                elif "role" in sources:
                    st.caption(f"Sources : {SOURCE_LABEL} et rôles municipaux officiels synchronisés · résultats publics, non enregistrés automatiquement.")
                else:
                    st.caption(f"Source : {SOURCE_LABEL} · résultats publics, non enregistrés automatiquement.")
        st.caption("Après votre consentement, cette action peut d’abord révéler la valeur au rôle municipal; ImmoValue reste une estimation marchande distincte, calculable avec au moins trois comparables autorisés.")
        st.button(
            "Rechercher et révéler les renseignements disponibles",
            key="address_lookup_submit",
            type="primary",
            on_click=_submit_address_lookup,
        )
        st.caption("Adresse saisie et renseignements publics éventuels restent séparés des calculs ImmoValue et ImmoScore.")
    address_lookup = st.session_state.get(ADDRESS_LOOKUP_KEY)
    # Public results must be visible immediately after their explicit search.
    # They are not contingent on calculating private financial assumptions.
    _show_role_overview(address_lookup)
    step, completed = _ensure_workflow_state()
    st.progress(step / len(STEPS), text=f"Étape {step}/{len(STEPS)} — {STEPS[step-1]}")
    st.selectbox(
        "Étape du parcours", list(range(1, len(STEPS) + 1)), key="analysis_step_selector",
        format_func=lambda value: f"{value}. {STEPS[value-1]}", on_change=_choose_workflow_step,
    )
    if step == 1:
        st.selectbox("Que souhaitez-vous faire?", list(ANALYSIS_OBJECTIVES), key="workflow_objective_choice")
        chosen_objective = st.session_state.get("workflow_objective_choice", "")
        if chosen_objective:
            st.session_state["workflow_objective"] = chosen_objective
            st.session_state["workflow_profile"] = ANALYSIS_OBJECTIVES[chosen_objective]
        st.caption("Le dossier adapte sa lecture à cet objectif. Vous pourrez toujours ajuster votre profil dans Mon compte; les dossiers existants ne sont pas modifiés.")
    elif step == 2:
        st.text_input("Nom descriptif de la propriété", key="workflow_property_name", placeholder="Ex. Duplex à Beauharnois")
        st.selectbox("Type de propriété", ["", "Maison", "Condo", "Duplex", "Triplex", "Immeuble"], key="workflow_property_type")
    previous, next_step, _ = st.columns([1, 1, 3])
    previous.button("Précédent", disabled=step == 1, on_click=_previous_workflow_step)
    next_step.button("Suivant", disabled=step == len(STEPS), on_click=_next_workflow_step)
    for workflow_error in st.session_state.get("workflow_errors", []):
        st.error(workflow_error)
    st.caption("Les valeurs restent dans le brouillon de cette session; une analyse n'est sauvegardée dans l'historique qu'après votre confirmation.")
    st.write("Saisissez vos hypothèses pour obtenir une analyse financière claire et personnalisée. Les calculs sont reproductibles et présentés avant impôt.")
    with st.expander("Portée de l'analyse"):
        st.write("ImmoRadar fonde ses résultats sur les renseignements et hypothèses fournis. La qualité de l'analyse dépend donc de leur exactitude et de leur exhaustivité.")
    st.button("Réinitialiser l'analyse", on_click=reset_analysis, type="secondary")

    with st.expander("Acquisition et financement — étape 3", expanded=step == 3):
        acquisition, financing = st.columns(2)
        with acquisition:
            st.number_input("Prix de la propriété ($)", min_value=0.0, step=5_000.0, key="property_price")
            st.number_input("Mise de fonds ($)", min_value=0.0, step=5_000.0, key="down_payment")
            st.number_input("Travaux initiaux ($)", min_value=0.0, step=1_000.0, key="initial_repairs")
            st.number_input("Frais d'acquisition ($)", min_value=0.0, step=1_000.0, key="acquisition_costs")
        with financing:
            st.number_input("Taux hypothécaire annuel (%)", min_value=0.0, max_value=25.0, step=0.05, format="%.2f", key="mortgage_rate")
            st.number_input("Amortissement (années)", min_value=5, max_value=30, step=1, key="amortization_years")
            st.number_input("Revenu brut annuel du ménage ($, facultatif)", min_value=0.0, step=5_000.0, key="household_income")
            st.number_input("Autres dettes mensuelles ($, facultatif)", min_value=0.0, step=100.0, key="other_debts")

    with st.expander("Revenus et dépenses d'exploitation — étape 4", expanded=step == 4):
        revenue, monthly, annual = st.columns(3)
        with revenue:
            st.number_input("Revenus locatifs mensuels ($)", min_value=0.0, step=100.0, key="rental_income")
            st.number_input("Autres revenus mensuels ($)", min_value=0.0, step=50.0, key="other_income")
            st.number_input("Taux de vacance (%)", min_value=0.0, max_value=100.0, step=0.5, key="vacancy_rate")
        with monthly:
            st.number_input("Assurances mensuelles ($)", min_value=0.0, step=25.0, key="insurance")
            st.number_input("Frais de copropriété mensuels ($)", min_value=0.0, step=25.0, key="condo_fees")
            st.number_input("Entretien courant mensuel ($)", min_value=0.0, step=25.0, key="maintenance")
            st.number_input("Frais de gestion mensuels ($)", min_value=0.0, step=25.0, key="management")
            st.number_input("Services publics mensuels ($)", min_value=0.0, step=25.0, key="utilities")
            st.number_input("Réserve mensuelle dépenses majeures ($)", min_value=0.0, step=25.0, key="capital_reserve")
            st.number_input("Autres dépenses mensuelles ($)", min_value=0.0, step=25.0, key="other_expenses")
        with annual:
            st.number_input("Taxes municipales annuelles ($)", min_value=0.0, step=100.0, key="municipal_taxes")
            st.number_input("Taxes scolaires annuelles ($)", min_value=0.0, step=50.0, key="school_taxes")

    with st.expander("Hypothèses de projection — étape 8", expanded=step == 8):
        growth, horizon = st.columns(2)
        with growth:
            st.number_input("Croissance annuelle hypothétique des loyers (%)", min_value=-25.0, max_value=25.0, step=0.25, key="rent_growth")
            st.number_input("Croissance annuelle hypothétique des dépenses (%)", min_value=-25.0, max_value=25.0, step=0.25, key="expense_growth")
        with horizon:
            st.number_input("Horizon de détention (années)", min_value=1, max_value=40, step=1, key="holding_period")
        st.caption("Ces projections utilisent uniquement vos taux de croissance déclarés. Elles ne prévoient pas le marché ni la valeur future de la propriété.")

    inputs = _inputs_from_state()
    signature = _analysis_signature(inputs)
    if st.button("Calculer / mettre à jour mon analyse", type="primary", key="calculate_analysis"):
        errors = validate_inputs(inputs)
        if errors:
            st.session_state["analysis_calculation_requested"] = True
            st.session_state.pop("analysis_calculation_signature", None)
            st.session_state["analysis_calculation_errors"] = errors
        else:
            st.session_state["analysis_calculation_requested"] = True
            st.session_state["analysis_calculation_signature"] = signature
            st.session_state["analysis_calculation_errors"] = []
    if st.session_state.get("analysis_calculation_requested") and st.session_state.get("analysis_calculation_signature") != signature:
        st.session_state.pop("analysis_calculation_signature", None)
    for error in st.session_state.get("analysis_calculation_errors", []):
        st.error(error)
    if st.session_state.get("analysis_calculation_signature") != signature:
        st.info("Aucune analyse personnelle n’est affichée avant votre calcul. Saisissez vos hypothèses puis choisissez « Calculer / mettre à jour mon analyse ».")
        return
    if is_authenticated():
        profile = st.session_state["workflow_profile"]
        st.caption(f"Profil ImmoEngine appliqué : {profile}. Les nouvelles analyses utilisent l’objectif choisi; les dossiers existants restent inchangés.")
    else:
        profile = st.session_state["workflow_profile"]
        st.caption("Créez un compte pour enregistrer votre profil et sauvegarder cette analyse.")
    _show_results(inputs, calculate_analysis(inputs), profile, address_lookup)


def _show_role_overview(address_lookup: dict | None) -> None:
    """Show official assessment data only as a clearly labelled fiscal reference."""

    if not address_lookup:
        return
    st.markdown("<div class='official-result-heading'><p class='eyebrow'>RENSEIGNEMENTS PUBLICS DU DOSSIER</p><h2>Rôle municipal</h2></div>", unsafe_allow_html=True)
    state = st.session_state.get(ADDRESS_STATE_KEY)
    if state and state.address:
        address = state.address
        postal = f", {address.postal_code}" if address.postal_code else ""
        unit = f", {address.unit}" if address.unit else ""
        st.caption(f"Adresse normalisée : {address.street}{unit}, {address.city}{postal}")
    elif address_lookup.get("normalized_address"):
        address = address_lookup["normalized_address"]
        st.caption(f"Adresse publique : {address['street']}, {address['city']}")
        if not address_lookup.get("postal_available", True):
            st.info("Le code postal n’est pas publié dans ce rôle municipal. Vous pouvez le saisir manuellement; cela ne bloque pas l’affichage de cette valeur officielle.")
    if not address_lookup.get("consent"):
        st.info("Recherche publique non autorisée : activez le consentement puis lancez la recherche, ou continuez manuellement.")
        return
    if address_lookup.get("coverage") is False:
        st.info("Aucun territoire municipal actif et synchronisé n’est disponible pour cette municipalité. Continuez manuellement ou demandez à un administrateur de synchroniser le territoire.")
        return
    matches = address_lookup.get("matches", [])
    if matches:
        chosen = st.selectbox("Unité officielle trouvée", range(len(matches)), key="official_role_unit", format_func=lambda index: matches[index]["address_text"] or matches[index]["matricule"] or "Unité officielle")
        match = matches[chosen]
        st.markdown("<article class='official-role-card'><span class='data-pill real'>Valeur municipale officielle</span><h3>Valeur au rôle — ce n’est pas une valeur marchande</h3></article>", unsafe_allow_html=True)
        land, building, total = st.columns(3)
        land.metric("Terrain", _money(match["land_value"] or 0))
        building.metric("Bâtiment", _money(match["building_value"] or 0))
        total.metric("Total au rôle", _money(match["total_value"] or 0))
        st.caption(f"Rôle {match['role_year']} · date de référence {match['market_reference_date'] or 'non publiée'} · source MAMH / Données Québec · licence CC BY 4.0. Cette valeur n’est jamais appliquée automatiquement à ImmoValue ou à vos finances.")
        return
    variants = address_lookup.get("variants", [])
    detail = f" Variante publique disponible : {', '.join(variants)}." if variants else ""
    st.info("Le territoire est synchronisé, mais aucune unité officielle ne correspond exactement aux renseignements saisis. Vérifiez le numéro ou la voie, ou poursuivez manuellement." + detail)


def _show_results(inputs: PropertyInputs, result: AnalysisResult, profile: str, address_lookup: dict | None = None) -> None:
    st.markdown("<div class='section-space compact-space'></div><h2>Votre dossier immobilier 360</h2><p class='section-intro'>Commencez par la vue d’ensemble, puis consultez les chiffres, les vérifications et la provenance.</p>", unsafe_allow_html=True)
    overview_tab, finances_tab, risks_tab, details_tab = st.tabs(["Vue d’ensemble", "Finances", "Risques et vérifications", "Détails et sources"])
    engine_result = evaluate_immoengine(inputs, result, profile)
    with overview_tab:
        immovalue = _show_immovalue()
        score, confidence, verdict = st.columns(3)
        score.metric("Score ImmoRadar", f"{engine_result.score:.0f} / 100" if engine_result.score is not None else "Indisponible")
        confidence.metric("Confiance", f"{engine_result.confidence_index} / 100")
        verdict.metric("Lecture", engine_result.verdict.capitalize())
        st.caption("La confiance décrit la qualité et la complétude des renseignements saisis; elle ne garantit pas une décision.")
        strengths, checks = st.columns(2)
        with strengths:
            st.subheader("Points forts")
            for item in engine_result.positive_factors[:3] or ["Indisponible tant que les hypothèses requises ne sont pas fournies."]:
                st.success(item)
        with checks:
            st.subheader("À vérifier")
            for item in (engine_result.negative_factors + engine_result.missing_data)[:3] or ["Ajoutez des renseignements pour obtenir des vérifications ciblées."]:
                st.warning(item)
    with finances_tab:
        st.subheader("Les chiffres de votre projet")
        first, second, third = st.columns(3)
        first.metric("Paiement hypothécaire", _money(result.monthly_payment))
        second.metric("Revenus effectifs mensuels", _money(result.effective_rental_income_monthly))
        third.metric("Flux de trésorerie mensuel", _money(result.cash_flow_monthly))
        a, b, c = st.columns(3)
        a.metric("RNE annuel", _money(result.net_operating_income_annual))
        b.metric("Capital réellement investi", _money(result.actual_capital_invested))
        c.metric("Rendement sur capital", f"{result.cash_on_cash_return:.2f} %")
        d, e, f = st.columns(3)
        d.metric("Taux de capitalisation", f"{result.capitalization_rate:.2f} %")
        e.metric("DSCR", f"{result.debt_service_coverage_ratio:.2f}x")
        f.metric("Marge mensuelle de sécurité", _money(result.monthly_safety_margin))
        if result.housing_cost_ratio is not None:
            st.info(f"Ratio déclaré des coûts de logement et autres dettes : {result.housing_cost_ratio:.1f} %. Méthode : (paiement hypothécaire + dépenses d'exploitation + autres dettes) / revenu brut mensuel. Ce n'est pas un critère officiel de prêteur.")
        else:
            st.caption("Abordabilité indisponible : ajoutez le revenu brut annuel du ménage pour calculer le ratio déclaré des coûts de logement.")
        st.caption(f"Projection à {inputs.holding_period_years} ans : flux mensuel hypothétique {_money(result.projected_cash_flow_monthly)}, fondé seulement sur les croissances de loyers et dépenses saisies.")
    with risks_tab:
        show_immoengine_result(engine_result)
        scenarios, resilience = show_scenarios(inputs, engine_result.profile)
    with details_tab:
        st.subheader("Méthode et limites")
        st.write("ImmoValue est une fourchette expérimentale issue des comparables que vous fournissez. Le rôle municipal est une valeur fiscale officielle, distincte d’une valeur marchande. ImmoScore mesure l’adéquation de vos hypothèses à votre profil; il ne constitue pas une recommandation.")
        st.caption("Chaque renseignement officiel affiché indique sa provenance, son année et sa fraîcheur. Une donnée absente reste indisponible.")

    st.markdown("<div class='save-analysis-panel'><h3>Sauvegarder et activer le suivi</h3><p>La sauvegarde crée votre dossier. Les alertes restent limitées aux changements réellement calculables et à votre forfait.</p>", unsafe_allow_html=True)
    if is_authenticated():
        property_name = st.text_input("Nom ou adresse de la propriété", key="saved_property_name", placeholder="Ex. Duplex - Montréal")
        if st.button("Sauvegarder dans Mes propriétés", type="primary", key="save_analysis"):
            if not property_name.strip():
                st.error("Veuillez donner un nom ou une adresse à cette analyse.")
            else:
                save_analysis(current_user()["id"], property_name, {
                    "price": inputs.price, "down_payment": inputs.down_payment,
                    "rental_income": inputs.rental_income_monthly, "monthly_expenses": result.total_monthly_expenses,
                    "cash_flow": result.cash_flow_monthly, "cash_on_cash_return": result.cash_on_cash_return,
                    "capitalization_rate": result.capitalization_rate,
                    "debt_service_coverage_ratio": result.debt_service_coverage_ratio,
                    "financial_inputs": asdict(inputs), "scenarios": scenarios, "resilience": resilience,
                    "market_context": market_context_snapshot(str(DATABASE_PATH)),
                    "immovalue": immovalue,
                }, profile=engine_result.profile, engine_result=engine_result)
                st.success("Dossier, scénarios et tests de résistance sauvegardés dans Mes propriétés.")
    else:
        st.write("Connectez-vous pour conserver cette analyse, ses scénarios et ses tests de résistance.")
        st.button("Créer un compte ou se connecter", on_click=go_to, args=("Mon compte",), key="save_analysis_login")
    st.markdown("</div>", unsafe_allow_html=True)


def _show_immovalue() -> dict:
    """A local-only workspace; declared comparables stay separate from financial scoring."""
    st.markdown("<div class='section-space'></div><h2>Estimation ImmoValue</h2>", unsafe_allow_html=True)
    st.warning("ImmoValue expérimental — fondé sur les informations et comparables fournis par l'utilisateur. Il ne constitue pas une évaluation officielle.")
    with st.expander("1. Informations sur la propriété et 3. Comparables manuels", expanded=False):
        a, b, c = st.columns(3)
        with a:
            name = st.text_input("Adresse ou nom déclaré", key="iv_name")
            property_type = st.selectbox("Type déclaré", ["", "Maison", "Condo", "Duplex", "Triplex", "Immeuble"], key="iv_type")
            units = st.number_input("Unités déclarées", 0, 20, key="iv_units")
        with b:
            living_area = st.number_input("Superficie habitable déclarée", 0.0, key="iv_area")
            land_area = st.number_input("Terrain déclaré", 0.0, key="iv_land")
            year = st.number_input("Année de construction déclarée", 0, 2100, key="iv_year")
        with c:
            asking = st.number_input("Prix demandé facultatif", 0.0, key="iv_asking")
            st.text_area("Rénovations et notes déclarées", key="iv_notes")
        st.caption("Tous les renseignements ci-dessus sont déclarés par l'utilisateur et non vérifiés.")
        st.download_button("Télécharger le modèle CSV", csv_template(), "comparables-immoradar.csv", "text/csv")
        uploaded = st.file_uploader("Importer un CSV local (jamais transmis à un service externe)", type="csv", key="comparables_csv")
        sales_confirmed = st.checkbox("Je confirme que les lignes représentent des ventes conclues", key="csv_sales_confirmed")
        import_rights = st.checkbox("Je confirme mon droit d'utilisation pour ce fichier", key="csv_import_rights")
        if uploaded:
            valid_rows, row_errors = validate_csv_rows(uploaded.getvalue().decode("utf-8-sig", errors="replace"), import_rights, sales_confirmed)
            st.caption(f"Prévisualisation locale : {len(valid_rows)} ligne(s) valide(s), {len(row_errors)} erreur(s).")
            if valid_rows: st.dataframe(valid_rows, hide_index=True, width="stretch")
            for error in row_errors: st.error(f"Ligne {error['line']} : {error['error']}")
            if st.button("Importer les lignes valides", disabled=not valid_rows, key="confirm_csv_import"):
                st.session_state["iv_csv_comparables"] = valid_rows; st.success("Lignes valides importées localement.")
            if st.button("Annuler l'import", key="cancel_csv_import"):
                st.session_state.pop("iv_csv_comparables", None); st.info("Import annulé sans sauvegarde.")
        comparables=list(st.session_state.get("iv_csv_comparables", []))
        for index in range(3):
            st.markdown(f"**Comparable {index + 1}**")
            x, y, z = st.columns(3)
            with x:
                address=st.text_input("Adresse ou identifiant", key=f"iv_address_{index}")
                sale_price=st.number_input("Prix de vente", 0.0, key=f"iv_price_{index}")
                area=st.number_input("Superficie", 0.0, key=f"iv_carea_{index}")
            with y:
                ctype=st.selectbox("Type", ["", "Maison", "Condo", "Duplex", "Triplex", "Immeuble"], key=f"iv_ctype_{index}")
                distance=st.number_input("Distance approximative (km)", 0.0, key=f"iv_distance_{index}")
                c_units=st.number_input("Unités", 0, 20, key=f"iv_cunits_{index}")
            with z:
                source=st.text_input("Source déclarée", key=f"iv_source_{index}")
                closed=st.checkbox("Vente conclue déclarée (pas une annonce active)", key=f"iv_closed_{index}")
                rights=st.checkbox("Je confirme disposer du droit d'utilisation", key=f"iv_rights_{index}")
            comparables.append({"address": address, "sale_date": "2026-01-01", "sale_price": sale_price, "living_area": area, "property_type": ctype, "units": c_units, "distance_km": distance, "source_declared": source, "declared_closed_sale": closed, "usage_right_confirmed": rights})
    subject=SubjectProperty(name=name, property_type=property_type, units=units or None, living_area=living_area or None, land_area=land_area or None, year_built=year or None, asking_price=asking or None, notes=st.session_state.get("iv_notes", ""))
    draft_key = f"immovalue:{hash((subject.name, subject.living_area, tuple(str(item) for item in comparables)))}"
    # A connected user may open or resume an analysis before requesting an
    # estimate.  Always render the deterministic availability state first;
    # quota consumption remains limited to the explicit generation action.
    estimate = st.session_state.get("immovalue_generated_result") or estimate_immovalue(subject, comparables)
    if is_authenticated():
        user=current_user(); quota=quota_status(user["id"],user,DATABASE_PATH)
        st.caption(quota["label"] + (" · Le quota est désactivé pendant la bêta." if not _quota_enforced() else ""))
        if st.button("Produire l'estimation ImmoValue", type="primary", key="generate_immovalue"):
            candidate=estimate_immovalue(subject, comparables)
            if not candidate["available"]:
                st.info("Estimation indisponible : ajoutez au moins trois comparables admissibles.")
            elif not _quota_enforced() or consume_estimation(user["id"],user,DATABASE_PATH,draft_key):
                st.session_state["immovalue_generated_result"]=candidate;estimate=candidate;st.success("Estimation produite.")
            else:
                st.warning("Votre estimation gratuite du mois est utilisée. L'analyse financière reste disponible.")
                st.button("Découvrir Premium",on_click=go_to,args=("Premium",))
    else:
        estimate=estimate_immovalue(subject, comparables)
    if estimate["available"]:
        one, two, three = st.columns(3); one.metric("Valeur expérimentale", f"{estimate['estimated_value']:,.0f} $".replace(',', ' ')); two.metric("Fourchette prudente", f"{estimate['low']:,.0f} $ à {estimate['high']:,.0f} $".replace(',', ' ')); three.metric("Confiance ImmoValue", f"{estimate['confidence']} / 100")
        st.caption(f"{estimate['used_count']} comparables utilisés · dispersion {estimate['dispersion_pct']} % · {estimate['method']}")
        if estimate["asking_comparison"]: st.info(f"Prix demandé : {estimate['asking_comparison']} (écart indicatif {estimate['asking_gap']:,.0f} $).")
    else: st.info("Aucune estimation : ajoutez au moins trois comparables admissibles et la superficie du sujet.")
    if estimate["comparables"]:
        st.dataframe([{"Comparable": item.get("address") or "Non renseigné", "Statut": item["status"], "Similarité": f"{item['similarity']:.0f} / 100", "Raison": item["reason"]} for item in estimate["comparables"]], hide_index=True, width="stretch")
    st.caption("ImmoValue est séparé d'ImmoScore : cette estimation n'influence pas le score financier et décisionnel.")
    return estimate


def _quota_enforced() -> bool:
    from repositories.sqlite_repository import SQLiteRepository
    with SQLiteRepository(DATABASE_PATH)._connect() as connection:
        row=connection.execute("SELECT quota_enforced FROM beta_settings WHERE id=1").fetchone()
    return bool(row and row[0])
