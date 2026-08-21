"""Complete property analysis UI with enriched assumptions and deterministic scenarios."""

from dataclasses import asdict
from datetime import date
import hashlib
import json
import re
import unicodedata

import streamlit as st

from calculations.real_estate import AnalysisResult, PropertyInputs, calculate_analysis, validate_inputs
from components.account import current_user, is_authenticated
from components.live_text_input import live_text_input
from components.immoengine import show_immoengine_result
from components.premium_teaser import show_premium_teaser
from components.scenarios import show_scenarios
from components.sidebar import go_to
from data.database import save_analysis
from data.database import DATABASE_PATH
from domain.immoengine import PROFILE_WEIGHTS, evaluate_immoengine
from domain.scenarios import build_resilience_tests, build_standard_scenarios
from services.market_data_service import market_context_snapshot
from domain.immovalue import SubjectProperty, estimate_immovalue
from services.comparable_csv import csv_template, validate_csv_rows
from services.comparable_workspace import (
    PROPERTY_TYPES,
    comparison_conclusion,
    duplicate_comparable,
    reviewed_comparables,
    today_iso,
)
from services.analysis_workflow import STEPS, load_draft, save_draft, normalize_step, transition
from services.entitlements_service import can_use, quota_is_enforced, quota_status, consume_estimation
from services.dossier_tracking_service import (
    DossierTrackingAccessError,
    dossier_fingerprint,
    set_dossier_tracking,
    tracked_dossier_fingerprints,
)
from services.address_lookup_service import lookup
from services.quebec_role_importer import display_role_address,search_role_units,role_street_variants,suggest_role_units
from services.quebec_role_admin_service import territory_for_municipality
from services.quebec_role_auto_sync import AutoSyncResult, municipal_coverage_status, synchronize_selected_municipality
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
    "expense_growth": 0.0, "holding_period": 5, "mortgage_renewal_date": None,
}

ANALYSIS_OBJECTIVES = {
    "Acheter pour y habiter": "Premier acheteur",
    "Investir et louer": "Investisseur locatif",
    "Connaître la valeur de ma propriété": "Propriétaire",
    "Préparer une vente": "Propriétaire",
}

VISIBLE_ANALYSIS_STAGES = (
    (1, "Propriété et valeur", "Choisissez la propriété et voyez les renseignements publics disponibles."),
    (2, "Finances", "Ajoutez les chiffres de votre projet, puis calculez votre analyse."),
    (3, "Résultats et rapport", "Consultez les résultats, sauvegardez votre dossier ou produisez un rapport."),
)

# A municipal assessment roll is an official fiscal reference, not a live
# market appraisal.  Keep this explanation identical wherever the three
# values are compared so the role is never mistaken for ImmoValue.
MUNICIPAL_VALUE_CONTEXT = (
    "La valeur au rôle municipal est un repère fiscal officiel établi à une date de référence. "
    "Elle peut être plus élevée ou plus basse que le prix du marché actuel, notamment selon "
    "l’année du rôle, le secteur et l’évolution récente du marché. Ce n’est pas une estimation marchande."
)

ADDRESS_STATE_KEY = "address_form_state"
ADDRESS_LOOKUP_KEY = "address_form_lookup"
ADDRESS_OWNER_KEY = "address_form_owner"
ADDRESS_HYDRATE_KEY = "address_form_hydrate"
ADDRESS_SUGGESTIONS_KEY = "address_form_suggestions"
ADDRESS_SUGGESTION_QUERY_KEY = "address_form_suggestion_query"
ADDRESS_AUTOCOMPLETE_KEY = "address_form_autocomplete"
ADDRESS_EDITOR_STREET_KEY = "address_form_editor_street"
ADDRESS_STREET_INPUT_KEY = "address_form_street_input"
ADDRESS_MANUAL_MODE_KEY = "address_form_manual_mode"
ADDRESS_RESOLUTION_KEY = "address_form_resolution"
ADDRESS_RESOLUTION_SELECTION_KEY = "address_form_resolution_selection"
ADDRESS_LOCAL_SELECTED_KEY = "address_form_local_selected"
ADDRESS_AUTO_SYNC_PENDING_KEY = "address_form_auto_sync_pending"
ADDRESS_AUTO_SYNC_STATUS_KEY = "address_form_auto_sync_status"
ANALYSIS_REOPEN_PENDING_KEY = "analysis_reopen_pending"
LAST_SAVED_ANALYSIS_KEY = "last_saved_analysis"
MAX_ADDRESS_SUGGESTIONS = 6
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


def _apply_reopen_draft() -> str | None:
    """Apply one ownership-scoped saved snapshot before widgets are rendered."""

    payload = st.session_state.pop(ANALYSIS_REOPEN_PENDING_KEY, None)
    if not isinstance(payload, dict) or not is_authenticated():
        return None
    if payload.get("owner_id") != current_user().get("id"):
        return None
    for key, value in payload.get("financial_values", {}).items():
        if key in DEFAULTS and isinstance(value, (int, float)) and not isinstance(value, bool):
            st.session_state[key] = value
    st.session_state["iv_asking"] = payload.get("asking_price") or 0.0
    st.session_state["workflow_property_name"] = str(payload.get("property_name") or "")
    st.session_state["workflow_property_type"] = str(payload.get("property_type") or "")
    objective = str(payload.get("objective") or "")
    st.session_state["workflow_objective"] = objective if objective in ANALYSIS_OBJECTIVES else ""
    st.session_state["workflow_objective_choice"] = st.session_state["workflow_objective"]
    st.session_state["workflow_profile"] = str(payload.get("profile") or "")
    renewal_date = payload.get("mortgage_renewal_date")
    if isinstance(renewal_date, str):
        try:
            st.session_state["mortgage_renewal_date"] = date.fromisoformat(renewal_date)
        except ValueError:
            st.session_state["mortgage_renewal_date"] = None
    else:
        # An older snapshot has no renewal date. Never keep the prior draft's
        # date when opening it as a fresh editable dossier.
        st.session_state["mortgage_renewal_date"] = None
    st.session_state["analysis_step"] = 1
    st.session_state["analysis_completed_steps"] = {1}
    st.session_state["analysis_reopen_show_property_stage"] = True
    st.session_state["workflow_errors"] = []
    st.session_state["address_form_start_empty"] = True
    st.session_state.pop("analysis_calculation_signature", None)
    st.session_state.pop("analysis_calculation_requested", None)
    st.session_state.pop("analysis_calculation_errors", None)
    return "Dossier ouvert dans un nouveau brouillon. Vérifiez vos chiffres avant de recalculer; aucune recherche publique n’a été relancée."


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
    st.session_state[ADDRESS_STREET_INPUT_KEY] = state.values["street"]
    # Clear the legacy component state so an old browser session cannot retain
    # a second suggestions menu after switching to the native editor.
    st.session_state.pop(ADDRESS_AUTOCOMPLETE_KEY, None)


def _address_state_for_current_user() -> AddressFormState:
    """Load exactly one canonical state for the active user/session."""
    owner_id = _address_owner_id()
    start_empty = bool(st.session_state.pop("address_form_start_empty", False))
    if start_empty:
        state = empty_address_form_state()
        st.session_state[ADDRESS_OWNER_KEY] = owner_id
        st.session_state[ADDRESS_STATE_KEY] = state
        st.session_state[ADDRESS_HYDRATE_KEY] = True
        st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
        st.session_state.pop(ADDRESS_LOCAL_SELECTED_KEY, None)
        st.session_state.pop(ADDRESS_RESOLUTION_KEY, None)
        _clear_address_suggestions()
    # Anonymous sessions use ``None`` as their owner id.  Test key presence,
    # not only equality, or a fresh anonymous session would skip its first
    # canonical hydration (including the Accueil → Analyser hand-off).
    if not start_empty and (ADDRESS_OWNER_KEY not in st.session_state or st.session_state.get(ADDRESS_OWNER_KEY) != owner_id):
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
            elif ADDRESS_STREET_INPUT_KEY in st.session_state:
                values["street"] = st.session_state[ADDRESS_STREET_INPUT_KEY]
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
    # Restoring a role-backed draft uses only the local, already-imported
    # public record. It never calls the external geocoder again.
    if (
        state.valid
        and state.metadata.get("official_source") == "role"
        and ADDRESS_LOOKUP_KEY not in st.session_state
    ):
        st.session_state[ADDRESS_LOOKUP_KEY] = _official_lookup_fields(
            state.address.street, state.address.city, bool(state.values.get("consent")), postal_available=False,
        )
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


def _queue_auto_role_sync(state: AddressFormState) -> None:
    """Queue one consented municipal lookup; the next render performs it once."""

    if not state.valid or not state.address or not state.values.get("consent"):
        return
    # An imported local-role match is already authoritative; never redownload it.
    if state.metadata.get("official_source") == "role":
        return
    st.session_state[ADDRESS_AUTO_SYNC_PENDING_KEY] = {"street": state.address.street, "city": state.address.city}


def _run_queued_auto_role_sync() -> AutoSyncResult | None:
    """Synchronize one exact territory after selecting a consented public address."""

    pending = st.session_state.pop(ADDRESS_AUTO_SYNC_PENDING_KEY, None)
    state = st.session_state.get(ADDRESS_STATE_KEY)
    if not isinstance(pending, dict) or not isinstance(state, AddressFormState) or not state.valid or not state.address:
        return None
    if pending.get("street") != state.address.street or pending.get("city") != state.address.city:
        return None
    with st.status("Vérification des données officielles", expanded=False) as status:
        result = synchronize_selected_municipality(DATABASE_PATH, state.address.city, bool(state.values.get("consent")))
        if result.status in {"available", "synchronized"}:
            status.update(label="Renseignements disponibles", state="complete")
            st.session_state[ADDRESS_LOOKUP_KEY] = _official_lookup(state)
        elif result.status == "in_progress":
            status.update(label="Synchronisation de cette municipalité", state="running")
        elif result.status == "unsupported_format":
            status.update(label="Format du rôle municipal non pris en charge", state="error")
        else:
            status.update(label="Renseignements officiels indisponibles", state="error")
    st.session_state[ADDRESS_AUTO_SYNC_STATUS_KEY] = result.status
    if result.status not in {"available", "synchronized", "in_progress"}:
        st.error(result.message)
    return result


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
    st.session_state.pop(ADDRESS_LOCAL_SELECTED_KEY, None)
    st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
    st.session_state.pop(ADDRESS_AUTO_SYNC_PENDING_KEY, None)


def _set_address_editor_street(value: str) -> None:
    """Keep the transient editor in sync without saving a draft prematurely."""

    state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
    values = dict(state.values)
    current_street = str(values.get("street", ""))
    # streamlit-searchbox can replay the partial search term on the rerun
    # immediately following a click.  A role-backed selection is already a
    # verified public match: keep it while that term is merely a prefix of
    # the selected street, but still invalidate it for a genuinely different
    # address typed by the person.
    if (
        state.metadata.get("official_source") in {"role", "external"}
        and _street_query_matches_selection(value, current_street)
    ):
        st.session_state[ADDRESS_EDITOR_STREET_KEY] = current_street
        return
    # Searchbox reruns may repeat the selected text. Keep a confirmed public
    # result until the person has actually changed the address.
    if useful_query(value) == useful_query(current_street):
        st.session_state[ADDRESS_EDITOR_STREET_KEY] = value
        return
    values["street"] = value
    errors = {name: message for name, message in state.errors.items() if name != "street"}
    st.session_state[ADDRESS_EDITOR_STREET_KEY] = value
    st.session_state[ADDRESS_STATE_KEY] = AddressFormState(values=values, address=None, errors=errors)
    st.session_state.pop(ADDRESS_LOCAL_SELECTED_KEY, None)
    st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
    st.session_state.pop(ADDRESS_AUTO_SYNC_PENDING_KEY, None)


def _street_query_matches_selection(query: str, selected: str) -> bool:
    """Return whether a replayed search term still describes one selection."""

    def key(value: str) -> str:
        text = unicodedata.normalize("NFD", useful_query(value).casefold())
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = re.sub(r"\b(rue|avenue|av\.?|boulevard|boul\.?|chemin|route|rang|place|montee)\b", " ", text)
        return "".join(char for char in text if char.isalnum())

    query_key, selected_key = key(query), key(selected)
    return bool(query_key and selected_key and selected_key.startswith(query_key))


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
        for row in suggest_role_units(DATABASE_PATH, query, limit=MAX_ADDRESS_SUGGESTIONS)
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
    # Providers do not always use the same street-type spelling as the
    # municipal role (for example, "Rue" can be omitted). Compare the
    # structured street and city, not the display label or its postal code.
    value = " ".join((suggestion.street, suggestion.city)).strip() or suggestion.label
    value = re.sub(
        r"\b[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ]\s?\d[ABCEGHJKLMNPRSTVWXYZ]\d\b",
        "",
        value,
        flags=re.I,
    )
    value = re.sub(r"\b(rue|avenue|av\.?|boulevard|boul\.?|chemin|route|rang|place|montee)\b", " ", value, flags=re.I)
    value = "".join(char for char in unicodedata.normalize("NFD", value.casefold()) if not unicodedata.combining(char))
    return "".join(char for char in value if char.isalnum())


def _merge_address_suggestions(external: tuple[AddressSuggestion, ...], local: list[AddressSuggestion]) -> list[AddressSuggestion]:
    """Return one compact list, enriching a matching local role when possible."""

    merged: list[AddressSuggestion] = []
    positions: dict[str, int] = {}
    for suggestion in (*local, *external):
        key = _suggestion_key(suggestion)
        if not key:
            continue
        position = positions.get(key)
        if position is None:
            positions[key] = len(merged)
            merged.append(suggestion)
            continue
        current = merged[position]
        # A role unit is directly linked to its municipal values. Preserve that
        # link while adding an official postal code exposed by MRNF's label.
        if current.source == "role" and suggestion.source != "role" and not current.postal_code:
            postal_match = re.search(r"\b[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ]\s?\d[ABCEGHJKLMNPRSTVWXYZ]\d\b", suggestion.label, re.I)
            postal = normalize_canadian_postal_code(postal_match.group(0)) if postal_match else ""
            if postal:
                merged[position] = AddressSuggestion(
                    street=current.street,
                    city=current.city,
                    postal_code=postal,
                    unit=current.unit,
                    label=" · ".join(part for part in (current.street, current.city, postal) if part),
                    source="role",
                )
    return merged[:MAX_ADDRESS_SUGGESTIONS]


def _same_public_address(left: AddressSuggestion, right: AddressSuggestion) -> bool:
    """Match a role address to a geocoded candidate without guessing."""

    def key(value: str, *, street: bool) -> str:
        text = unicodedata.normalize("NFD", value.casefold())
        text = "".join(char for char in text if not unicodedata.combining(char))
        if street:
            text = re.sub(r"\b(rue|avenue|av\.?|boulevard|boul\.?|chemin|route|rang|place|montee)\b", " ", text)
        return "".join(char for char in text if char.isalnum())

    return bool(
        left.street and right.street and left.city and right.city
        and key(left.street, street=True) == key(right.street, street=True)
        and key(left.city, street=False) == key(right.city, street=False)
    )


def _same_suggestion_text(left: AddressSuggestion, right: AddressSuggestion) -> bool:
    """Compare public selection text without retaining provider payloads."""

    def key(value: str) -> str:
        text = unicodedata.normalize("NFD", value.casefold())
        return "".join(char for char in text if char.isalnum() and not unicodedata.combining(char))

    return bool(left.label and right.label and key(left.label) == key(right.label))


def _enrich_local_suggestion(selected: AddressSuggestion, consent: bool) -> AddressSuggestion | None:
    """Use MRNF after a click to fill a postal code absent from a role.

    An unavailable enrichment is intentionally silent: the selected local role
    remains valid public information and must never be replaced by an error.
    """

    if not consent:
        return None
    try:
        enabled = source_enabled(SOURCE_ID, DATABASE_PATH)
    except Exception:
        enabled = False
    if not enabled:
        return None
    response = resolve_freeform_address(f"{selected.street}, {selected.city}", True)
    if response.status != "ok":
        return None
    for candidate in response.suggestions:
        if _same_public_address(selected, candidate):
            return candidate
    return None


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


def _show_municipal_coverage_hint() -> None:
    """Show a local-only, actionable coverage state before a lookup.

    The form only reads the local official-index cache here: merely rendering
    this hint must never start a public request.
    """

    if not st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False):
        return
    if st.session_state.get(ADDRESS_MANUAL_MODE_KEY, False):
        return
    city = useful_query(st.session_state.get(ADDRESS_WIDGET_KEYS["city"], ""))
    if not city:
        return
    try:
        status = municipal_coverage_status(DATABASE_PATH, city)["status"]
    except Exception:
        # A local cache issue must never block the manual path or expose a
        # city name in a technical diagnostic.
        return
    latest = st.session_state.get(ADDRESS_AUTO_SYNC_STATUS_KEY)
    if latest == "unsupported_format":
        st.warning("Couverture municipale : le format officiel de cette municipalité n’est pas encore compatible. Vous pouvez poursuivre manuellement.")
    elif status == "available":
        st.success("Couverture municipale prête : les renseignements officiels sont déjà disponibles pour cette municipalité.")
    elif status == "sync_available":
        st.info("Couverture municipale possible : après votre recherche consentie, ImmoRadar synchronisera uniquement cette municipalité.")
    elif status == "retry_later":
        st.warning("Couverture municipale à réessayer : une synchronisation récente a échoué. Vous pouvez poursuivre manuellement.")
    elif status in {"source_disabled", "territory_disabled"}:
        st.info("Couverture municipale indisponible : cette source officielle est désactivée. Vous pouvez poursuivre manuellement.")
    else:
        st.info("Couverture municipale non confirmée : aucun rôle officiel ne peut être relié avec certitude. Vous pouvez poursuivre manuellement.")


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
    consent = bool(st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False))
    # The official endpoint resolves an opaque selection key only after a
    # click. A local role result is already authoritative; an exact MRNF match
    # can enrich it with a postal code but failure must not remove the role.
    if selected.source == "role":
        resolved = _enrich_local_suggestion(selected, consent) or selected
    else:
        resolved = resolve_suggestion(selected, consent)
        if resolved is None:
            # Some official type-ahead responses expose a key that cannot be
            # resolved again by the provider. Retry the same, already
            # consented public label through the documented free-form
            # operation and accept only an exact public match.
            fallback = resolve_freeform_address(selected.label, consent)
            if fallback.status == "ok":
                resolved = next(
                    (candidate for candidate in fallback.suggestions if _same_suggestion_text(selected, candidate)),
                    None,
                )
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
            "consent": consent,
        }
    )
    metadata = {
        "official_source": selected.source,
        "postal_optional": selected.source == "role" and not bool(resolved.postal_code),
    }
    selected_state = submit_address_form(
        values["street"],
        values["city"],
        values["postal"],
        values["unit"],
        consent,
        allow_missing_postal=bool(metadata["postal_optional"]),
        metadata=metadata,
    )
    st.session_state[ADDRESS_STATE_KEY] = selected_state
    st.session_state[ADDRESS_EDITOR_STREET_KEY] = resolved.street
    st.session_state[ADDRESS_STREET_INPUT_KEY] = resolved.street
    # This callback runs before the adjacent editors are instantiated in the
    # same rerun, so they can safely receive the selected canonical values.
    st.session_state[ADDRESS_WIDGET_KEYS["city"]] = values["city"]
    st.session_state[ADDRESS_WIDGET_KEYS["postal"]] = values["postal"]
    st.session_state[ADDRESS_WIDGET_KEYS["unit"]] = values["unit"]
    st.session_state[ADDRESS_HYDRATE_KEY] = True
    st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
    if selected.source == "role":
        st.session_state[ADDRESS_LOCAL_SELECTED_KEY] = True
    else:
        st.session_state.pop(ADDRESS_LOCAL_SELECTED_KEY, None)
    if selected_state.valid:
        st.session_state[ADDRESS_LOOKUP_KEY] = _official_lookup(selected_state)
        _queue_auto_role_sync(selected_state)
    _persist_address_draft(selected_state)
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
    selected_state = submit_address_form(
        values["street"], values["city"], values["postal"], values.get("unit", ""),
        bool(values.get("consent")), metadata={"official_source": "external"},
    )
    st.session_state[ADDRESS_STATE_KEY] = selected_state
    st.session_state[ADDRESS_HYDRATE_KEY] = True
    st.session_state[ADDRESS_EDITOR_STREET_KEY] = values["street"]
    st.session_state[ADDRESS_WIDGET_KEYS["city"]] = values["city"]
    st.session_state[ADDRESS_WIDGET_KEYS["postal"]] = values["postal"]
    if selected_state.valid:
        st.session_state[ADDRESS_LOOKUP_KEY] = _official_lookup(selected_state)
        _queue_auto_role_sync(selected_state)
        _persist_address_draft(selected_state)


def _submit_address_lookup() -> None:
    """Validate and persist the exact same widget values in one explicit action."""
    street = st.session_state.get(ADDRESS_EDITOR_STREET_KEY, st.session_state.get(ADDRESS_WIDGET_KEYS["street"], ""))
    city = st.session_state.get(ADDRESS_WIDGET_KEYS["city"], "")
    postal = st.session_state.get(ADDRESS_WIDGET_KEYS["postal"], "")
    consent = bool(st.session_state.get(ADDRESS_WIDGET_KEYS["consent"], False))
    current_state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
    local_selection = bool(current_state.metadata.get("official_source") == "role")
    st.session_state.pop(ADDRESS_RESOLUTION_KEY, None)
    # A copied address from Accueil often has no separate city/postal fields.
    # Resolve it only here, after an explicit consented action; ambiguity is
    # left to the person instead of guessing a municipality or unit.
    if consent and street and (not city or not postal) and not local_selection:
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
            st.session_state[ADDRESS_STREET_INPUT_KEY] = street
            st.session_state[ADDRESS_WIDGET_KEYS["city"]] = city
            st.session_state[ADDRESS_WIDGET_KEYS["postal"]] = postal
    state = submit_address_form(
        street,
        city,
        postal,
        st.session_state.get(ADDRESS_WIDGET_KEYS["unit"], ""),
        consent,
        allow_missing_postal=local_selection,
        metadata=current_state.metadata if local_selection else None,
    )
    st.session_state[ADDRESS_STATE_KEY] = state
    _persist_address_draft(state)
    if state.valid:
        st.session_state[ADDRESS_LOOKUP_KEY] = _official_lookup(state)
        _queue_auto_role_sync(state)
    else:
        st.session_state.pop(ADDRESS_LOOKUP_KEY, None)
    st.session_state[ADDRESS_HYDRATE_KEY] = True
    _clear_address_suggestions()


def _official_lookup(state: AddressFormState) -> dict:
    """Use the same canonical address for consent and the local official lookup."""
    assert state.address is not None
    local_role = state.metadata.get("official_source") == "role"
    result = None if local_role else lookup(state.address, state.values["consent"])
    response = _official_lookup_fields(
        state.address.street,
        state.address.city,
        state.values["consent"],
        postal_available=not bool(state.metadata.get("postal_optional", False)),
    )
    if result is not None:
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
    if state["step"] > 1:
        st.session_state.pop("analysis_reopen_show_property_stage", None)
    _persist_workflow(state["step"], state["completed"])


def _choose_workflow_step() -> None:
    _move_workflow(st.session_state.get("analysis_step_selector", 1))


def _previous_workflow_step() -> None:
    _move_workflow(st.session_state.get("analysis_step", 1) - 1)


def _next_workflow_step() -> None:
    _move_workflow(st.session_state.get("analysis_step", 1) + 1)


def _continue_to_finances() -> None:
    """Advance the compatible nine-step draft through the first visible stage."""

    _move_workflow(2)
    if not st.session_state.get("workflow_errors"):
        _move_workflow(3)


def _analysis_is_calculated(inputs: PropertyInputs) -> bool:
    """Keep personal results behind the existing explicit calculation action."""

    return st.session_state.get("analysis_calculation_signature") == _analysis_signature(inputs)


def _visible_analysis_stage(step: int, calculated: bool, has_financial_data: bool = False) -> int:
    """Map the preserved technical workflow to the three public-facing stages."""

    if calculated:
        return 3
    return 1 if step <= 2 and not has_financial_data else 2


def _current_role_match(address_lookup: dict | None) -> dict | None:
    """Return the selected official match without inventing a public value."""

    matches = (address_lookup or {}).get("matches", [])
    if not matches:
        return None
    try:
        selected = int(st.session_state.get("official_role_unit", 0))
    except (TypeError, ValueError):
        selected = 0
    return matches[max(0, min(selected, len(matches) - 1))]


def _show_dossier_summary(address_state: AddressFormState, address_lookup: dict | None, inputs: PropertyInputs, profile: str) -> None:
    """Show only known facts and explicitly mark every unavailable result."""

    if not address_state.address:
        return
    role_match = _current_role_match(address_lookup)
    calculated = _analysis_is_calculated(inputs)
    engine_result = evaluate_immoengine(inputs, calculate_analysis(inputs), profile) if calculated else None
    immovalue = st.session_state.get("immovalue_generated_result")
    if not isinstance(immovalue, dict) or not immovalue.get("available"):
        immovalue = None

    address = address_state.address
    postal = f", {address.postal_code}" if address.postal_code else ""
    unit = f", {address.unit}" if address.unit else ""
    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>RÉSUMÉ DU DOSSIER</p><h2>Ce qu’ImmoRadar sait pour l’instant</h2>", unsafe_allow_html=True)
    st.caption(f"Adresse normalisée : {address.street}{unit}, {address.city}{postal}")
    official, market, finances = st.columns(3)
    with official:
        with st.container(border=True):
            st.markdown("### Valeur officielle")
            if role_match:
                st.metric("Valeur au rôle municipal", _money(role_match["total_value"] or 0))
                st.caption(f"Rôle {role_match['role_year']} · MAMH / Données Québec")
                st.caption("Repère fiscal officiel : il peut différer du prix du marché actuel.")
            else:
                st.metric("Valeur au rôle municipal", "Données nécessaires")
                st.caption("Choisissez une adresse couverte ou poursuivez manuellement.")
    with market:
        with st.container(border=True):
            st.markdown("### Estimation marchande")
            if immovalue:
                st.metric("Fourchette ImmoValue", f"{_money(immovalue['low'])} à {_money(immovalue['high'])}")
                st.caption(f"Expérimental · confiance {immovalue['confidence']} / 100")
            else:
                st.metric("ImmoValue", "À calculer")
                st.caption("Ajoutez au moins trois comparables autorisés pour une estimation expérimentale.")
    with finances:
        with st.container(border=True):
            st.markdown("### Analyse financière")
            if engine_result and engine_result.score is not None:
                st.metric("Score ImmoRadar", f"{engine_result.score:.0f} / 100")
                st.caption(f"{engine_result.verdict.capitalize()} · confiance {engine_result.confidence_index} / 100")
            else:
                st.metric("Score ImmoRadar", "À calculer")
                st.caption("Ajoutez les chiffres de votre projet puis lancez l’analyse.")

    if role_match and calculated:
        orientation = "La valeur municipale et votre analyse sont prêtes. Consultez ensuite les résultats et les vérifications."
    elif role_match:
        orientation = "La valeur municipale est disponible. Ajoutez vos chiffres pour comprendre les finances de votre projet."
    else:
        orientation = "Ajoutez ou choisissez une propriété pour révéler les renseignements publics disponibles, puis complétez vos chiffres."
    st.info(orientation)


def _show_visible_stage_progress(active_stage: int) -> None:
    """Keep progress obvious without exposing nine technical steps by default."""

    columns = st.columns(3)
    for column, (number, title, description) in zip(columns, VISIBLE_ANALYSIS_STAGES):
        with column:
            with st.container(border=True):
                state = "En cours" if number == active_stage else "À venir" if number > active_stage else "Terminé"
                st.markdown(f"<p class='eyebrow'>ÉTAPE {number} · {state.upper()}</p><h3>{title}</h3><p class='section-intro'>{description}</p>", unsafe_allow_html=True)


def _hydrate_dossier_name_from_selected_address() -> None:
    """Use a selected official address as the optional dossier label, never overwriting a custom name."""

    if useful_query(st.session_state.get("workflow_property_name", "")):
        return
    state = st.session_state.get(ADDRESS_STATE_KEY)
    if not isinstance(state, AddressFormState) or not state.address:
        return
    if state.metadata.get("official_source") not in {"role", "external"}:
        return
    address = state.address
    st.session_state["workflow_property_name"] = ", ".join(part for part in (address.street, address.city) if part)


def _show_property_stage() -> None:
    """Render the simple first stage while retaining the existing workflow values."""

    st.markdown("<div class='section-space compact-space'></div><h2>1. Propriété et valeur</h2><p class='section-intro'>Choisissez votre objectif, puis recherchez la propriété dans le bloc ci-dessus.</p>", unsafe_allow_html=True)
    # Keep the established first-run default so the first visible step is
    # immediately usable.  Reopened dossiers provide their original objective
    # before this widget is created, therefore it remains selected there.
    st.selectbox("Votre objectif", list(ANALYSIS_OBJECTIVES), key="workflow_objective_choice")
    chosen_objective = st.session_state.get("workflow_objective_choice", "")
    if chosen_objective:
        st.session_state["workflow_objective"] = chosen_objective
        st.session_state["workflow_profile"] = ANALYSIS_OBJECTIVES[chosen_objective]
    _hydrate_dossier_name_from_selected_address()
    name, kind, asking = st.columns(3)
    with name:
        st.text_input("Nom court du dossier (facultatif si une adresse est sélectionnée)", key="workflow_property_name", placeholder="Ex. Projet résidentiel")
    with kind:
        st.selectbox("Type de propriété (requis)", ["", "Maison", "Condo", "Duplex", "Triplex", "Immeuble"], key="workflow_property_type")
    with asking:
        st.number_input("Prix demandé (facultatif)", min_value=0.0, step=5_000.0, key="iv_asking")
    st.caption("Le prix demandé sert uniquement à comparer le rôle municipal et ImmoValue lorsqu’elle est disponible. Il ne remplace pas le prix retenu pour vos calculs financiers.")
    st.caption("Ces renseignements servent à organiser votre dossier. La recherche publique et les calculs restent séparés.")
    st.button("Continuer vers les finances", type="primary", key="continue_to_finances", on_click=_continue_to_finances)


def _show_finance_stage() -> None:
    """Render the useful financial inputs first; less common inputs stay available."""

    st.markdown("<div class='section-space compact-space'></div><h2>2. Vos chiffres</h2><p class='section-intro'>Ajoutez les montants que vous connaissez. Les résultats ne sont affichés qu’après votre calcul.</p>", unsafe_allow_html=True)
    acquisition, financing = st.columns(2)
    with acquisition:
        st.number_input("Prix retenu pour vos calculs ($)", min_value=0.0, step=5_000.0, key="property_price")
        st.number_input("Mise de fonds ($)", min_value=0.0, step=5_000.0, key="down_payment")
        st.number_input("Revenus locatifs mensuels ($)", min_value=0.0, step=100.0, key="rental_income")
        st.number_input("Autres dépenses mensuelles ($)", min_value=0.0, step=25.0, key="other_expenses")
    with financing:
        st.number_input("Taux hypothécaire annuel (%)", min_value=0.0, max_value=25.0, step=0.05, format="%.2f", key="mortgage_rate")
        st.number_input("Amortissement (années)", min_value=5, max_value=30, step=1, key="amortization_years")
        st.number_input("Taxes municipales annuelles ($)", min_value=0.0, step=100.0, key="municipal_taxes")
        st.number_input("Assurances mensuelles ($)", min_value=0.0, step=25.0, key="insurance")
    st.caption("Le prix retenu peut correspondre au prix demandé, à votre offre ou à une autre hypothèse. Il reste distinct du rôle municipal et d’ImmoValue.")

    with st.expander("Options avancées", expanded=False):
        st.caption("Ces champs restent facultatifs. Ils améliorent la précision de votre lecture sans modifier les formules.")
        first, second, third = st.columns(3)
        with first:
            st.number_input("Travaux initiaux ($)", min_value=0.0, step=1_000.0, key="initial_repairs")
            st.number_input("Frais d'acquisition ($)", min_value=0.0, step=1_000.0, key="acquisition_costs")
            st.number_input("Autres revenus mensuels ($)", min_value=0.0, step=50.0, key="other_income")
            st.number_input("Taux de vacance (%)", min_value=0.0, max_value=100.0, step=0.5, key="vacancy_rate")
            st.number_input("Revenu brut annuel du ménage ($, facultatif)", min_value=0.0, step=5_000.0, key="household_income")
            st.number_input("Autres dettes mensuelles ($, facultatif)", min_value=0.0, step=100.0, key="other_debts")
        with second:
            st.number_input("Taxes scolaires annuelles ($)", min_value=0.0, step=50.0, key="school_taxes")
            st.number_input("Frais de copropriété mensuels ($)", min_value=0.0, step=25.0, key="condo_fees")
            st.number_input("Entretien courant mensuel ($)", min_value=0.0, step=25.0, key="maintenance")
            st.number_input("Frais de gestion mensuels ($)", min_value=0.0, step=25.0, key="management")
            st.number_input("Services publics mensuels ($)", min_value=0.0, step=25.0, key="utilities")
            st.number_input("Réserve mensuelle dépenses majeures ($)", min_value=0.0, step=25.0, key="capital_reserve")
        with third:
            st.number_input("Croissance annuelle hypothétique des loyers (%)", min_value=-25.0, max_value=25.0, step=0.25, key="rent_growth")
            st.number_input("Croissance annuelle hypothétique des dépenses (%)", min_value=-25.0, max_value=25.0, step=0.25, key="expense_growth")
            st.number_input("Horizon de détention (années)", min_value=1, max_value=40, step=1, key="holding_period")
            st.date_input("Date de renouvellement hypothécaire (facultatif)", value=None, key="mortgage_renewal_date")
            st.caption("Elle sert seulement à afficher un rappel local dans vos alertes suivies. Aucun courriel n’est envoyé.")
            st.caption("Les projections utilisent uniquement les taux que vous saisissez. Elles ne prévoient pas le marché ni une valeur future.")
        st.button("Réinitialiser les chiffres", on_click=reset_analysis, type="secondary", key="reset_analysis")


def _show_technical_workflow(step: int) -> None:
    """Keep the resumable nine-step workflow accessible without making it the main path."""

    with st.expander("Parcours détaillé (facultatif)", expanded=False):
        st.progress(step / len(STEPS), text=f"Progression détaillée : {step}/{len(STEPS)} — {STEPS[step - 1]}")
        st.selectbox(
            "Étape détaillée", list(range(1, len(STEPS) + 1)), key="analysis_step_selector",
            format_func=lambda value: f"{value}. {STEPS[value - 1]}", on_change=_choose_workflow_step,
        )
        previous, next_step, _ = st.columns([1, 1, 3])
        previous.button("Précédent", disabled=step == 1, on_click=_previous_workflow_step)
        next_step.button("Suivant", disabled=step == len(STEPS), on_click=_next_workflow_step)
        st.caption("Le parcours détaillé est conservé pour reprendre un brouillon existant. La vue principale reste organisée en trois étapes.")


def show_property_analysis() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    reopen_notice = _apply_reopen_draft()
    st.markdown("<p class='eyebrow'>DOSSIER IMMOBILIER 360</p>", unsafe_allow_html=True)
    st.title("Révéler la valeur et analyser votre projet")
    st.markdown("<p class='section-intro'>Adresse, renseignements publics autorisés, valeur disponible, finances et suivi : un seul dossier, sans transformer les données manquantes en conclusions.</p>", unsafe_allow_html=True)
    if reopen_notice:
        st.success(reopen_notice)
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
            editor_street = live_text_input(
                label="Adresse",
                placeholder="Ex. 123 rue Exemple",
                value=address_state.values["street"],
                key=ADDRESS_STREET_INPUT_KEY,
                debounce_ms=400,
            )
            suggestion_actions = st.empty()
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
            st.caption("La couverture des rôles municipaux officiels n’est pas encore complète pour tout le Québec. Si aucun rôle n’est disponible, vous pouvez poursuivre manuellement.")
        _show_municipal_coverage_hint()
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
        current_state = st.session_state.get(ADDRESS_STATE_KEY, empty_address_form_state())
        selected_street = current_state.values.get("street", "")
        # The keyup component may briefly return its pre-click value during
        # the rerun that follows a server-rendered suggestion click. Never let
        # that transient blank overwrite a verified public selection.
        if (
            current_state.valid
            and current_state.metadata.get("official_source") in {"role", "external"}
            and not useful_query(editor_street)
        ):
            editor_street = selected_street
        _set_address_editor_street(editor_street)
        editor_street = st.session_state.get(ADDRESS_EDITOR_STREET_KEY, editor_street)
        current_query = useful_query(editor_street)
        if (
            current_state.valid
            and current_state.metadata.get("official_source") in {"role", "external"}
            and useful_query(editor_street) == useful_query(selected_street)
        ):
            _clear_address_suggestions()
        else:
            _autocomplete_options(editor_street)
        suggestion_response = st.session_state.get(ADDRESS_SUGGESTIONS_KEY)
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
                # The live component opens a list while typing. Keep an
                # accessible Streamlit action for the same ephemeral options
                # as well: it makes selection reliable on every supported
                # browser/component combination, without storing an address
                # or requiring Enter, Tab or a second search.
                with suggestion_actions.container(height=220, border=False):
                    st.caption("Choisissez une suggestion pour remplir les renseignements disponibles.")
                    for index, suggestion in enumerate(suggestion_response.suggestions):
                        st.button(
                            suggestion.label,
                            key=f"address_suggestion_select_{index}",
                            on_click=_select_address_suggestion,
                            args=(suggestion.to_option(),),
                            use_container_width=True,
                        )
        address_lookup = st.session_state.get(ADDRESS_LOOKUP_KEY)
        if not _has_revealed_public_information(address_lookup):
            st.caption("Après votre consentement, cette action peut d’abord révéler la valeur au rôle municipal; ImmoValue reste une estimation marchande distincte, calculable avec au moins trois comparables autorisés.")
            st.button(
                "Rechercher et révéler les renseignements disponibles",
                key="address_lookup_submit",
                type="primary",
                on_click=_submit_address_lookup,
            )
        st.caption("Adresse saisie et renseignements publics éventuels restent séparés des calculs ImmoValue et ImmoScore.")
    _run_queued_auto_role_sync()
    address_state = st.session_state.get(ADDRESS_STATE_KEY, address_state)
    address_lookup = st.session_state.get(ADDRESS_LOOKUP_KEY)
    # Public results must be visible immediately after their explicit search.
    # They are not contingent on calculating private financial assumptions.
    if _has_revealed_public_information(address_lookup):
        st.success("Renseignements publics révélés ✓")
    step, completed = _ensure_workflow_state()
    inputs = _inputs_from_state()
    profile = st.session_state["workflow_profile"]
    calculated = _analysis_is_calculated(inputs)
    _show_dossier_summary(address_state, address_lookup, inputs, profile)
    _show_role_overview(address_lookup)
    visible_stage = (
        1
        if st.session_state.get("analysis_reopen_show_property_stage")
        else _visible_analysis_stage(step, calculated, bool(inputs.price or inputs.down_payment))
    )
    _show_visible_stage_progress(visible_stage)
    if visible_stage == 1:
        _show_property_stage()
    elif visible_stage == 2:
        _show_finance_stage()
    else:
        st.markdown("<div class='section-space compact-space'></div><h2>3. Résultats et rapport</h2><p class='section-intro'>Votre analyse est prête. Consultez la vue d’ensemble, puis sauvegardez votre dossier ou produisez votre rapport.</p>", unsafe_allow_html=True)
    _show_technical_workflow(step)
    for workflow_error in st.session_state.get("workflow_errors", []):
        st.error(workflow_error)
    st.caption("Les chiffres restent dans votre brouillon de session. Un dossier n’est sauvegardé dans Mes propriétés qu’après votre confirmation.")
    signature = _analysis_signature(inputs)
    if visible_stage == 2 and st.button("Calculer mon analyse", type="primary", key="calculate_analysis"):
        errors = validate_inputs(inputs)
        if errors:
            st.session_state["analysis_calculation_requested"] = True
            st.session_state.pop("analysis_calculation_signature", None)
            st.session_state["analysis_calculation_errors"] = errors
        else:
            st.session_state["analysis_calculation_requested"] = True
            st.session_state["analysis_calculation_signature"] = signature
            st.session_state["analysis_calculation_errors"] = []
            st.success("Analyse calculée. Vos résultats sont prêts à consulter.")
    if st.session_state.get("analysis_calculation_requested") and st.session_state.get("analysis_calculation_signature") != signature:
        st.session_state.pop("analysis_calculation_signature", None)
    for error in st.session_state.get("analysis_calculation_errors", []):
        st.error(error)
    if st.session_state.get("analysis_calculation_signature") != signature:
        st.info("Aucune analyse personnelle n’est affichée avant votre calcul. Ajoutez vos chiffres, puis choisissez « Calculer mon analyse ».")
        return
    if is_authenticated():
        profile = st.session_state["workflow_profile"]
        st.caption(f"Profil ImmoEngine appliqué : {profile}. Les nouvelles analyses utilisent l’objectif choisi; les dossiers existants restent inchangés.")
    else:
        profile = st.session_state["workflow_profile"]
        st.caption("Créez un compte pour enregistrer votre profil et sauvegarder cette analyse.")
    _show_results(inputs, calculate_analysis(inputs), profile, address_lookup)


def _has_revealed_public_information(address_lookup: dict | None) -> bool:
    """Return true only when a consented lookup has an official role result to show."""

    return bool(address_lookup and address_lookup.get("consent") and address_lookup.get("matches"))


def _official_role_snapshot(address_lookup: dict | None) -> dict:
    """Keep only public fiscal fields needed to explain a future saved comparison."""
    if not address_lookup or not address_lookup.get("consent"):
        return {}
    matches = address_lookup.get("matches") or []
    selected = st.session_state.get("official_role_unit", 0)
    if not isinstance(selected, int) or not 0 <= selected < len(matches):
        selected = 0
    if not matches:
        return {}
    match = matches[selected]
    return {
        "land_value": match.get("land_value"),
        "building_value": match.get("building_value"),
        "total_value": match.get("total_value"),
        "role_year": match.get("role_year"),
        "reference_date": match.get("market_reference_date"),
        "source": "MAMH / Données Québec",
        "license": "CC BY 4.0",
    }


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
        sync_status = st.session_state.get(ADDRESS_AUTO_SYNC_STATUS_KEY)
        if sync_status == "unsupported_format":
            st.info("Le rôle municipal officiel de cette municipalité utilise un format qui n’est pas encore pris en charge. Vous pouvez poursuivre votre analyse manuellement.")
        elif sync_status in {"failed", "cooldown", "index_unavailable"}:
            st.info("La synchronisation de ce rôle municipal officiel n’est pas disponible pour le moment. Vous pouvez poursuivre votre analyse manuellement et réessayer plus tard.")
        elif sync_status == "territory_disabled":
            st.info("Ce rôle municipal est désactivé. Vous pouvez poursuivre votre analyse manuellement.")
        else:
            st.info("Aucun rôle municipal officiel synchronisé n’est disponible pour cette municipalité. Vous pouvez poursuivre votre analyse manuellement.")
        return
    matches = address_lookup.get("matches", [])
    if matches:
        chosen = st.selectbox(
            "Unité officielle trouvée", range(len(matches)), key="official_role_unit",
            format_func=lambda index: display_role_address(
                matches[index]["address_text"] or matches[index]["matricule"] or "Unité officielle"
            ),
        )
        match = matches[chosen]
        st.markdown("<article class='official-role-card'><span class='data-pill real'>Valeur municipale officielle</span><h3>Valeur au rôle — ce n’est pas une valeur marchande</h3></article>", unsafe_allow_html=True)
        land, building, total = st.columns(3)
        land.metric("Terrain", _money(match["land_value"] or 0))
        building.metric("Bâtiment", _money(match["building_value"] or 0))
        total.metric("Total au rôle", _money(match["total_value"] or 0))
        st.caption(f"Rôle {match['role_year']} · date de référence {match['market_reference_date'] or 'non publiée'} · source MAMH / Données Québec · licence CC BY 4.0. Cette valeur n’est jamais appliquée automatiquement à ImmoValue ou à vos finances.")
        st.info(MUNICIPAL_VALUE_CONTEXT)
        return
    variants = address_lookup.get("variants", [])
    detail = f" Variante publique disponible : {', '.join(variants)}." if variants else ""
    st.error("Le territoire est synchronisé, mais aucune unité officielle ne correspond exactement aux renseignements saisis. Vérifiez le numéro ou la voie, ou poursuivez manuellement." + detail)


def _summary_dossier_label() -> tuple[str, str]:
    """Use the selected address or custom label without inventing either."""

    state = st.session_state.get(ADDRESS_STATE_KEY)
    if isinstance(state, AddressFormState) and state.address:
        address = state.address
        return ", ".join(part for part in (address.street, address.city) if part), st.session_state.get("workflow_property_type", "")
    return st.session_state.get("workflow_property_name") or "Dossier immobilier", st.session_state.get("workflow_property_type", "")


def _generated_immovalue() -> dict | None:
    """Only an explicit ImmoValue action can populate the main synthesis."""

    value = st.session_state.get("immovalue_generated_result")
    return value if isinstance(value, dict) and value.get("available") else None


def _show_summary_financial_cards(inputs: PropertyInputs, result: AnalysisResult) -> None:
    """Present the seven useful indicators without presenting irrelevant zeros."""

    has_rental_context = bool(inputs.rental_income_monthly or inputs.other_income_monthly)
    items = (
        ("Paiement hypothécaire", _money(result.monthly_payment), "Montant mensuel lié au prêt."),
        ("Dépenses mensuelles", _money(result.total_monthly_expenses), "Frais d’exploitation et prêt."),
        ("Revenus locatifs", _money(result.effective_rental_income_monthly) if has_rental_context else "Non applicable", "Après la vacance déclarée." if has_rental_context else "Aucun revenu locatif saisi."),
        ("Flux de trésorerie", _money(result.cash_flow_monthly) if has_rental_context else "Non applicable", "Revenus moins dépenses." if has_rental_context else "Calcul locatif non applicable."),
        ("Taux de capitalisation", f"{result.capitalization_rate:.2f} %" if has_rental_context else "Non applicable", "RNE annuel / prix." if has_rental_context else "Dépend des revenus locatifs."),
        ("Rendement sur mise", f"{result.cash_on_cash_return:.2f} %" if has_rental_context else "Non applicable", "Flux annuel / capital investi." if has_rental_context else "Dépend des revenus locatifs."),
        ("Capacité à couvrir la dette (DSCR)", f"{result.debt_service_coverage_ratio:.2f}x" if has_rental_context else "Non applicable", "RNE annuel / dette." if has_rental_context else "Dépend des revenus locatifs."),
    )
    for group in (items[:4], items[4:]):
        columns = st.columns(len(group))
        for column, (label, value, description) in zip(columns, group):
            with column:
                with st.container(border=True):
                    st.metric(label, value)
                    st.caption(description)


def _show_summary_value_cards(address_lookup: dict | None, immovalue: dict | None) -> None:
    """Keep fiscal, estimated and asking values distinct and easy to scan."""

    role_match = _current_role_match(address_lookup)
    asking = float(st.session_state.get("iv_asking") or 0)
    official, market, asking_card = st.columns(3)
    with official:
        with st.container(border=True):
            st.markdown("**Valeur municipale officielle**")
            st.metric("Repère fiscal", _money(role_match["total_value"] or 0) if role_match else "À révéler")
            st.caption("Ce n’est pas une valeur marchande.")
    with market:
        with st.container(border=True):
            st.markdown("**Estimation ImmoValue**")
            st.metric("Fourchette", f"{_money(immovalue['low'])} à {_money(immovalue['high'])}" if immovalue else "À produire")
            st.caption(f"Expérimental · confiance {immovalue['confidence']} / 100" if immovalue else "Trois comparables admissibles sont requis.")
    with asking_card:
        with st.container(border=True):
            st.markdown("**Prix demandé**")
            st.metric("Prix saisi", _money(asking) if asking else "À ajouter")
            st.caption("Ajoutez-le dans ImmoValue pour comparer l’écart." if not asking else "Montant déclaré par vous.")
    st.info(MUNICIPAL_VALUE_CONTEXT)
    if immovalue and asking:
        gap = asking - immovalue["estimated_value"]
        st.info(f"Écart avec ImmoValue : {_money(gap)} ({gap / immovalue['estimated_value'] * 100:+.1f} %). {immovalue.get('asking_comparison') or ''}".strip())
    elif not immovalue:
        st.caption("ImmoValue reste à produire avec trois comparables admissibles.")
    elif not asking:
        st.caption("Ajoutez un prix demandé pour obtenir l’écart en dollars et en pourcentage.")


def _show_summary_scenarios(inputs: PropertyInputs, profile: str) -> None:
    """Compact preview of existing deterministic scenarios; no formula changes."""

    base = next(item for item in build_standard_scenarios(inputs, profile) if item.name == "Scénario de base")
    rate_up = next(item for item in build_resilience_tests(inputs, profile)[0] if item.name == "Taux +1 point")
    prudent = next(item for item in build_standard_scenarios(inputs, profile) if item.name == "Prudent")
    for column, scenario in zip(st.columns(3), (base, rate_up, prudent)):
        with column:
            with st.container(border=True):
                st.markdown(f"**{scenario.name}**")
                st.metric("Flux mensuel", _money(scenario.financial.cash_flow_monthly))
                st.caption(f"DSCR {scenario.financial.debt_service_coverage_ratio:.2f}x · {scenario.description}")


def _return_to_summary_inputs() -> None:
    st.session_state.pop("analysis_calculation_signature", None)
    st.session_state.pop("analysis_calculation_errors", None)
    st.session_state["analysis_calculation_requested"] = False


def _show_results(inputs: PropertyInputs, result: AnalysisResult, profile: str, address_lookup: dict | None = None) -> None:
    engine_result = evaluate_immoengine(inputs, result, profile)
    immovalue_preview = _generated_immovalue()
    dossier_label, property_type = _summary_dossier_label()
    st.markdown("<div class='section-space compact-space'></div><p class='eyebrow'>RÉSULTATS ET RAPPORT</p><h2>Votre synthèse immobilière</h2><p class='section-intro'>Les repères essentiels de votre dossier, séparés selon leur source et vos hypothèses.</p>", unsafe_allow_html=True)
    with st.container(border=True):
        identity, verdict = st.columns([3, 1])
        with identity:
            st.markdown(f"### {dossier_label}")
            st.caption(f"{property_type or 'Type de propriété à préciser'} · Analyse du {date.today().isoformat()}")
        with verdict:
            st.markdown(f"**{engine_result.verdict.capitalize()}**")
            st.caption("Lecture déterministe de vos hypothèses.")
        score, confidence = st.columns(2)
        score.metric("ImmoScore", f"{engine_result.score:.0f} / 100" if engine_result.score is not None else "Données insuffisantes")
        confidence.metric("Confiance", f"{engine_result.confidence_index} / 100")
        st.caption("Le score n’est pas une garantie. La confiance décrit la qualité et la complétude des données, pas la probabilité d’un bon achat.")

    st.subheader("Comparer les valeurs")
    _show_summary_value_cards(address_lookup, immovalue_preview)
    st.subheader("Les essentiels financiers")
    _show_summary_financial_cards(inputs, result)
    strengths, checks = st.columns(2)
    with strengths:
        st.subheader("Points forts")
        for item in engine_result.positive_factors[:3] or ["Aucun point fort déterministe n’est disponible avec les renseignements actuels."]:
            st.success(item)
    with checks:
        st.subheader("Points à vérifier")
        review_items = [*engine_result.negative_factors, *(f"Donnée à ajouter : {item}" for item in engine_result.missing_data)]
        for item in review_items[:3] or ["Aucun point à vérifier déterministe n’est disponible avec les renseignements actuels."]:
            st.warning(item)
    st.subheader("Scénarios en un coup d’œil")
    _show_summary_scenarios(inputs, engine_result.profile)

    overview_tab, finances_tab, risks_tab, details_tab = st.tabs([
        "Vue d’ensemble", "Finances", "Risques et vérifications", "Détails et sources",
    ])
    with overview_tab:
        immovalue = _show_immovalue(address_lookup)
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
        a.metric("Revenus nets annuels (RNE)", _money(result.net_operating_income_annual))
        b.metric("Capital réellement investi", _money(result.actual_capital_invested))
        c.metric("Rendement sur capital", f"{result.cash_on_cash_return:.2f} %")
        d, e, f = st.columns(3)
        d.metric("Taux de capitalisation", f"{result.capitalization_rate:.2f} %")
        e.metric("Capacité à couvrir la dette (DSCR)", f"{result.debt_service_coverage_ratio:.2f}x")
        f.metric("Marge mensuelle de sécurité", _money(result.monthly_safety_margin))
        if result.housing_cost_ratio is not None:
            st.info(f"Part déclarée du revenu consacrée au logement et aux dettes : {result.housing_cost_ratio:.1f} %. Calcul : paiement hypothécaire + revenus et dépenses du projet + autres dettes, divisé par le revenu brut mensuel. Ce n’est pas un critère officiel de prêteur.")
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

    st.markdown("<div class='save-analysis-panel'><h3>Enregistrer votre synthèse</h3><p>Sauvegardez ce dossier ou revenez aux chiffres saisis. Le suivi reste local : aucun courriel ni envoi automatique n’est activé pendant la bêta.</p>", unsafe_allow_html=True)
    action_save, action_edit, action_premium = st.columns(3)
    with action_edit:
        st.button("Modifier les hypothèses", on_click=_return_to_summary_inputs, key="edit_analysis_hypotheses", use_container_width=True)
    with action_premium:
        st.button("Voir les alertes Premium", on_click=go_to, args=("Premium",), key="summary_premium_preview", use_container_width=True)
    with action_save:
        st.caption("Le rapport PDF complet est disponible dans Mes propriétés avec Premium ou un accès administrateur de bêta.")
    if is_authenticated():
        property_name = st.text_input("Nom ou adresse de la propriété", key="saved_property_name", placeholder="Ex. Duplex - Montréal")
        if st.button("Sauvegarder dans Mes propriétés", type="primary", key="save_analysis"):
            if not property_name.strip():
                st.error("Veuillez donner un nom ou une adresse à cette analyse.")
            else:
                analysis_id = save_analysis(current_user()["id"], property_name, {
                    "price": inputs.price, "down_payment": inputs.down_payment,
                    "rental_income": inputs.rental_income_monthly, "monthly_expenses": result.total_monthly_expenses,
                    "cash_flow": result.cash_flow_monthly, "cash_on_cash_return": result.cash_on_cash_return,
                    "capitalization_rate": result.capitalization_rate,
                    "debt_service_coverage_ratio": result.debt_service_coverage_ratio,
                    "financial_inputs": {
                        **asdict(inputs),
                        "_analysis_objective": st.session_state.get("workflow_objective", ""),
                        "_property_type": st.session_state.get("workflow_property_type", ""),
                        "mortgage_renewal_date": (
                            st.session_state["mortgage_renewal_date"].isoformat()
                            if isinstance(st.session_state.get("mortgage_renewal_date"), date)
                            else None
                        ),
                    },
                    "market_context": market_context_snapshot(str(DATABASE_PATH)),
                    "immovalue": immovalue,
                    "official_role_snapshot": _official_role_snapshot(address_lookup),
                }, profile=engine_result.profile, engine_result=engine_result)
                st.session_state[LAST_SAVED_ANALYSIS_KEY] = {
                    "id": analysis_id,
                    "owner_id": current_user()["id"],
                    "property_name": property_name.strip(),
                }
                st.success("Dossier, scénarios et tests de résistance sauvegardés dans Mes propriétés.")
        saved = st.session_state.get(LAST_SAVED_ANALYSIS_KEY, {})
        if (
            isinstance(saved, dict)
            and saved.get("owner_id") == current_user()["id"]
            and saved.get("property_name") == property_name.strip()
            and isinstance(saved.get("id"), int)
        ):
            if can_use(current_user(), "alerts"):
                followed = dossier_fingerprint(current_user()["id"], property_name) in tracked_dossier_fingerprints(
                    current_user()["id"], DATABASE_PATH
                )
                label = "Suivi de ce dossier actif" if followed else "Activer le suivi de ce dossier"
                if st.button(label, key="activate_saved_dossier_tracking", disabled=followed):
                    try:
                        set_dossier_tracking(current_user()["id"], saved["id"], True, DATABASE_PATH)
                    except DossierTrackingAccessError:
                        st.error("Le dossier sauvegardé n’est plus disponible dans votre espace.")
                    else:
                        st.success("Suivi activé. Les alertes Premium liront seulement les changements vérifiables de ce dossier.")
                        st.rerun()
                if followed:
                    st.caption("Le suivi est actif. Vous pouvez le désactiver dans Mes propriétés.")
            else:
                st.caption("Le suivi des changements vérifiables est inclus dans l’aperçu Premium. Aucun courriel n’est activé pendant la bêta.")
    else:
        st.write("Connectez-vous pour conserver cette analyse, ses scénarios et ses tests de résistance.")
        st.button("Créer un compte ou se connecter", on_click=go_to, args=("Mon compte",), key="save_analysis_login")
    st.markdown("</div>", unsafe_allow_html=True)


def _immovalue_subject() -> SubjectProperty:
    """Collect the subject inputs without assigning an official value to it."""

    state = st.session_state.get(ADDRESS_STATE_KEY)
    address_name = ""
    if isinstance(state, AddressFormState) and state.address:
        address_name = ", ".join(part for part in (state.address.street, state.address.city) if part)
    name = st.text_input("Adresse ou nom de la propriété", key="iv_name", placeholder=address_name or "Ex. Projet résidentiel")
    first, second, third = st.columns(3)
    with first:
        property_type = st.selectbox("Type de propriété", PROPERTY_TYPES, key="iv_type")
    with second:
        living_area = st.number_input("Superficie habitable (pi² ou m², selon votre référence)", min_value=0.0, key="iv_area")
    with third:
        asking = st.number_input("Prix demandé (facultatif)", min_value=0.0, step=5_000.0, key="iv_asking")
    with st.expander("Détails de la propriété (facultatif)", expanded=False):
        a, b, c = st.columns(3)
        with a:
            units = st.number_input("Unités", min_value=0, max_value=20, key="iv_units")
        with b:
            land_area = st.number_input("Superficie du terrain", min_value=0.0, key="iv_land")
        with c:
            year = st.number_input("Année de construction", min_value=0, max_value=2100, key="iv_year")
        st.text_area("Notes personnelles sur la propriété (facultatif)", key="iv_notes")
    return SubjectProperty(
        name=name or address_name,
        property_type=property_type,
        units=st.session_state.get("iv_units") or None,
        living_area=living_area or None,
        land_area=st.session_state.get("iv_land") or None,
        year_built=st.session_state.get("iv_year") or None,
        asking_price=asking or None,
        notes=st.session_state.get("iv_notes", ""),
    )


def _comparable_from_form(prefix: str, current: dict | None = None) -> dict:
    """Render the minimum declared fields, with rarely used details collapsed."""

    current = current or {}
    one, two = st.columns(2)
    with one:
        address = st.text_input("Adresse ou nom descriptif", value=current.get("address", ""), key=f"{prefix}_address")
        sale_price = st.number_input("Prix de vente conclu ($)", min_value=0.0, step=5_000.0, value=float(current.get("sale_price") or 0), key=f"{prefix}_price")
        sale_date = st.date_input("Date de vente", value=current.get("sale_date") or today_iso(), key=f"{prefix}_date")
    with two:
        property_type = st.selectbox("Type de propriété", PROPERTY_TYPES, index=PROPERTY_TYPES.index(current.get("property_type", "")) if current.get("property_type", "") in PROPERTY_TYPES else 0, key=f"{prefix}_type")
        living_area = st.number_input("Superficie habitable", min_value=0.0, value=float(current.get("living_area") or 0), key=f"{prefix}_area")
        city = st.text_input("Ville", value=current.get("city", ""), key=f"{prefix}_city")
    source = st.text_input("Source ou provenance", value=current.get("source_declared", ""), key=f"{prefix}_source")
    closed = st.checkbox("Je confirme qu’il s’agit d’une vente conclue", value=bool(current.get("declared_closed_sale", False)), key=f"{prefix}_closed")
    rights = st.checkbox("Je confirme avoir le droit d’utiliser cette donnée", value=bool(current.get("usage_right_confirmed", False)), key=f"{prefix}_rights")
    with st.expander("Détails du comparable (facultatif)", expanded=False):
        a, b, c = st.columns(3)
        with a:
            land_area = st.number_input("Terrain", min_value=0.0, value=float(current.get("land_area") or 0), key=f"{prefix}_land")
            year_built = st.number_input("Année", min_value=0, max_value=2100, value=int(current.get("year_built") or 0), key=f"{prefix}_year")
        with b:
            bedrooms = st.number_input("Chambres", min_value=0, max_value=20, value=int(current.get("bedrooms") or 0), key=f"{prefix}_bedrooms")
            bathrooms = st.number_input("Salles de bain", min_value=0.0, max_value=20.0, value=float(current.get("bathrooms") or 0), key=f"{prefix}_bathrooms")
        with c:
            distance = st.number_input("Distance déclarée (km)", min_value=0.0, value=float(current.get("distance_km") or 0), key=f"{prefix}_distance")
            adjustment = st.number_input("Ajustement manuel ($)", value=float(current.get("manual_adjustment") or 0), step=1_000.0, key=f"{prefix}_adjustment")
            st.caption("Cet ajustement déclaré est visible dans la méthode; il n’est pas calculé automatiquement.")
    return {
        "guided_entry": True, "address": address.strip(), "sale_price": sale_price, "sale_date": sale_date.isoformat(),
        "property_type": property_type, "living_area": living_area, "city": city.strip(),
        "source_declared": source.strip(), "declared_closed_sale": closed, "usage_right_confirmed": rights,
        "land_area": land_area or None, "year_built": year_built or None, "bedrooms": bedrooms or None,
        "bathrooms": bathrooms or None, "distance_km": distance, "manual_adjustment": adjustment,
    }


def _stable_immovalue_key(subject: SubjectProperty, comparables: list[dict]) -> str:
    """Persistent idempotency key; changing a declared input creates a new action."""

    payload = {"subject": asdict(subject), "comparables": comparables}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
    return f"immovalue:{digest}"


def _show_immovalue(address_lookup: dict | None = None) -> dict:
    """Guide manual/CSV comparables without changing the ImmoValue algorithm."""

    st.markdown("<div class='section-space'></div><h2>Estimation marchande (ImmoValue)</h2>", unsafe_allow_html=True)
    st.caption("Expérimental : ajoutez vos ventes comparables autorisées. ImmoRadar ne collecte aucune transaction et ce résultat n’est pas une évaluation officielle.")
    subject = _immovalue_subject()
    st.session_state.setdefault("iv_manual_comparables", [])
    manual_comparables = list(st.session_state["iv_manual_comparables"])
    csv_comparables = list(st.session_state.get("iv_csv_comparables", []))
    comparables = [*manual_comparables, *csv_comparables]
    reviewed = reviewed_comparables(subject, comparables)
    admissible = sum(item["display_status"] == "Admissible" for item in reviewed)
    progress_label = "Estimation prête" if admissible >= 3 and subject.living_area else f"{admissible}/3 comparables admissibles"
    st.progress(min(admissible, 3) / 3, text=progress_label)
    if admissible < 3:
        st.caption("Ajoutez une vente à la fois. Trois comparables admissibles sont requis avant de produire une estimation.")
    elif not subject.living_area:
        st.info("Les comparables sont prêts. Ajoutez la superficie habitable de la propriété pour calculer ImmoValue.")

    with st.expander("Ajouter un comparable", expanded=admissible < 3):
        with st.form("iv_add_comparable"):
            candidate = _comparable_from_form("iv_add")
            submitted = st.form_submit_button("Ajouter ce comparable", type="primary")
        if submitted:
            existing = [*manual_comparables, *csv_comparables]
            if duplicate_comparable(candidate, existing):
                st.error("Ce comparable semble déjà présent (adresse, date et prix identiques).")
            else:
                st.session_state["iv_manual_comparables"] = [*manual_comparables, candidate]
                st.success("Comparable ajouté. Vérifiez son statut avant de produire l’estimation.")
                st.rerun()

    edit_index = st.session_state.get("iv_edit_comparable_index")
    if isinstance(edit_index, int) and 0 <= edit_index < len(manual_comparables):
        st.subheader(f"Modifier le comparable {edit_index + 1}")
        with st.form(f"iv_edit_comparable_{edit_index}"):
            edited = _comparable_from_form(f"iv_edit_{edit_index}", manual_comparables[edit_index])
            save_edit = st.form_submit_button("Enregistrer les modifications", type="primary")
        if save_edit:
            others = [item for index, item in enumerate(manual_comparables) if index != edit_index] + csv_comparables
            if duplicate_comparable(edited, others):
                st.error("Ce comparable semble déjà présent (adresse, date et prix identiques).")
            else:
                manual_comparables[edit_index] = edited
                st.session_state["iv_manual_comparables"] = manual_comparables
                st.session_state.pop("iv_edit_comparable_index", None)
                st.success("Comparable modifié.")
                st.rerun()

    if reviewed:
        st.subheader("Vos comparables")
        for index, item in enumerate(reviewed):
            source_kind = "Saisie guidée" if index < len(manual_comparables) else "Import CSV"
            with st.container(border=True):
                label, status_column, actions = st.columns([5, 2, 3])
                with label:
                    st.markdown(f"**{item.get('address') or 'Comparable sans nom'}** · {item.get('city') or 'Ville à préciser'}")
                    st.caption(f"{source_kind} · provenance : {item.get('source_declared') or 'à préciser'}")
                with status_column:
                    st.markdown(f"**{item['display_status']}**")
                    st.caption(item["display_reason"])
                with actions:
                    if index < len(manual_comparables):
                        if st.button("Modifier", key=f"iv_edit_{index}"):
                            st.session_state["iv_edit_comparable_index"] = index
                            st.rerun()
                        if st.button("Supprimer", key=f"iv_delete_{index}"):
                            st.session_state["iv_manual_comparables"] = [item for position, item in enumerate(manual_comparables) if position != index]
                            st.session_state.pop("iv_edit_comparable_index", None)
                            st.rerun()
                    else:
                        csv_index = index - len(manual_comparables)
                        if st.button("Retirer l’import", key=f"iv_delete_csv_{csv_index}"):
                            st.session_state["iv_csv_comparables"] = [item for position, item in enumerate(csv_comparables) if position != csv_index]
                            st.rerun()

    with st.expander("Import avancé (CSV local)", expanded=False):
        st.caption("Le fichier reste local. Utilisez l’assistant ci-dessus si vous préférez ajouter vos comparables un par un.")
        st.download_button("Télécharger le modèle CSV", csv_template(), "comparables-immoradar.csv", "text/csv")
        uploaded = st.file_uploader("Importer un CSV local (jamais transmis à un service externe)", type="csv", key="comparables_csv")
        sales_confirmed = st.checkbox("Je confirme que les lignes représentent des ventes conclues", key="csv_sales_confirmed")
        import_rights = st.checkbox("Je confirme mon droit d’utilisation pour ce fichier", key="csv_import_rights")
        if uploaded:
            valid_rows, row_errors = validate_csv_rows(uploaded.getvalue().decode("utf-8-sig", errors="replace"), import_rights, sales_confirmed)
            st.caption(f"Prévisualisation locale : {len(valid_rows)} ligne(s) valide(s), {len(row_errors)} erreur(s).")
            if valid_rows:
                st.dataframe(valid_rows, hide_index=True, width="stretch")
            for error in row_errors:
                st.error(f"Ligne {error['line']} : {error['error']}")
            if st.button("Importer les lignes valides", disabled=not valid_rows, key="confirm_csv_import"):
                unique = [item for item in valid_rows if not duplicate_comparable(item, [*manual_comparables, *csv_comparables])]
                st.session_state["iv_csv_comparables"] = [*csv_comparables, *unique]
                st.success(f"{len(unique)} ligne(s) valide(s) importée(s) localement.")
                st.rerun()
            if st.button("Annuler l’import", key="cancel_csv_import"):
                st.session_state.pop("iv_csv_comparables", None)
                st.info("Import annulé sans sauvegarde.")

    comparables = [*st.session_state.get("iv_manual_comparables", []), *st.session_state.get("iv_csv_comparables", [])]
    candidate = estimate_immovalue(subject, comparables)
    draft_key = _stable_immovalue_key(subject, comparables)
    generated = st.session_state.get("immovalue_generated_result")
    estimate = generated if st.session_state.get("immovalue_generated_key") == draft_key else None
    if generated and estimate is None:
        st.session_state.pop("immovalue_generated_result", None)
        st.session_state.pop("immovalue_generated_key", None)
        st.session_state.pop("immovalue_generated_at", None)

    if is_authenticated():
        user = current_user()
        quota = quota_status(user["id"], user, DATABASE_PATH)
        st.caption(quota["label"] + (" · Le quota est désactivé pendant la bêta." if not quota_is_enforced(DATABASE_PATH) else ""))
    if estimate is None:
        if not candidate["available"]:
            st.info("Estimation non prête : ajoutez les renseignements manquants et au moins trois comparables admissibles. Cette étape ne consomme aucune estimation.")
        elif st.button("Produire l’estimation ImmoValue", type="primary", key="generate_immovalue"):
            if not is_authenticated() or not quota_is_enforced(DATABASE_PATH) or consume_estimation(current_user()["id"], current_user(), DATABASE_PATH, draft_key):
                st.session_state["immovalue_generated_result"] = candidate
                st.session_state["immovalue_generated_key"] = draft_key
                st.session_state["immovalue_generated_at"] = today_iso()
                estimate = candidate
                st.success("Estimation ImmoValue produite.")
            else:
                st.warning("Votre estimation gratuite du mois est utilisée. L’analyse financière reste disponible.")
                show_premium_teaser(
                    feature="Estimations ImmoValue sans limite",
                    title="Continuez à évaluer les dossiers qui méritent votre attention.",
                    detail="Premium permet de produire d’autres estimations lorsqu’elles sont calculables avec au moins trois comparables admissibles.",
                    key="iv_premium",
                )

    if estimate and estimate["available"]:
        st.subheader("Comparer les valeurs")
        role_match = _current_role_match(address_lookup)
        official, market, asking_card = st.columns(3)
        with official:
            with st.container(border=True):
                st.markdown("**Valeur municipale officielle**")
                st.metric("Valeur au rôle", _money(role_match["total_value"] or 0) if role_match else "Indisponible")
                st.caption("Référence fiscale officielle, distincte d’une valeur marchande.")
        with market:
            with st.container(border=True):
                st.markdown("**Estimation ImmoValue**")
                st.metric("Valeur expérimentale", _money(estimate["estimated_value"]))
                st.caption(f"Fourchette : {_money(estimate['low'])} à {_money(estimate['high'])} · confiance {estimate['confidence']} / 100")
        with asking_card:
            with st.container(border=True):
                st.markdown("**Prix demandé**")
                st.metric("Prix saisi", _money(subject.asking_price) if subject.asking_price else "À ajouter")
                st.caption("Ajoutez un prix demandé pour visualiser l’écart avec ImmoValue." if not subject.asking_price else f"Écart : {_money(estimate['asking_gap'])} ({estimate['asking_gap'] / estimate['estimated_value'] * 100:+.1f} %)" )
        st.info(MUNICIPAL_VALUE_CONTEXT)
        st.info(comparison_conclusion(estimate))
        st.caption(f"Calculée le {st.session_state.get('immovalue_generated_at', today_iso())} · {estimate['used_count']} comparables admissibles · dispersion {estimate['dispersion_pct']} %.")
        with st.expander("Pourquoi cette estimation?", expanded=False):
            st.write("La valeur centrale est une médiane pondérée des prix par superficie des ventes déclarées admissibles. La pondération favorise les comparables les plus similaires; elle ne crée aucun ajustement automatique.")
            st.dataframe(
                [{
                    "Comparable": item.get("address") or "Non renseigné", "Statut": item["status"],
                    "Similarité": f"{item['similarity']:.0f} / 100", "Prix / superficie": _money(item.get("price_per_area") or 0),
                    "Provenance": item.get("source_declared") or "Non renseignée", "Ajustement déclaré": _money(item.get("manual_adjustment") or 0),
                    "Données manquantes / remarque": item["reason"],
                } for item in estimate["comparables"]],
                hide_index=True, width="stretch",
            )
            st.caption("Les ajustements manuels, la provenance déclarée et les données manquantes restent visibles. Les statistiques de marché agrégées ne servent pas de comparables individuels.")
    else:
        # Keep the declared subject snapshot even when three comparables are
        # not available yet. This preserves an optional asking price in a
        # saved dossier without presenting an ImmoValue result prematurely.
        estimate = candidate
    st.caption("ImmoValue est séparé d’ImmoScore : cette estimation n’influence pas le score financier et décisionnel.")
    return estimate

# Quota configuration is read centrally in services.entitlements_service.
