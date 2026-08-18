"""Consent-first suggestions from the official MRNF Adresses Québec geocoder.

Only the request needed by the user is sent to MRNF after explicit consent.
Coordinates, match scores and the raw payload are intentionally discarded and
are never passed to telemetry, diagnostics, drafts or application logs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import time
from typing import Any, Callable
from urllib.parse import urlencode, urlparse

import requests

from domain.address import normalize_canadian_postal_code


GEOCODER_URL = (
    "https://servicescarto.mrnf.gouv.qc.ca/pes/rest/services/"
    "Territoire/Adresse_Geocodage/GeocodeServer/findAddressCandidates"
)
SUGGEST_URL = (
    "https://servicescarto.mrnf.gouv.qc.ca/pes/rest/services/"
    "Territoire/Adresse_Geocodage/GeocodeServer/suggest"
)
SOURCE_ID = "mrnf_adresses_quebec_geocoder"
SOURCE_LABEL = "MRNF — Adresses Québec"
MIN_QUERY_CHARS = 3
MAX_QUERY_CHARS = 160
MAX_SUGGESTIONS = 8
REQUEST_TIMEOUT_SECONDS = 3.0
CACHE_TTL_SECONDS = 30.0
MIN_REQUEST_INTERVAL_SECONDS = 0.25


@dataclass(frozen=True)
class AddressSuggestion:
    """Only display/form fields supplied by the official service."""

    street: str
    city: str
    postal_code: str
    unit: str
    label: str
    lookup_key: str = ""
    source: str = "external"

    def to_dict(self) -> dict[str, str]:
        """Return display fields only; safe for UI assertions and exports."""

        return {
            "street": self.street,
            "city": self.city,
            "postal_code": self.postal_code,
            "unit": self.unit,
            "label": self.label,
        }

    def to_option(self) -> dict[str, str]:
        """Return the transient selection payload consumed by the searchbox."""

        return asdict(self)


@dataclass(frozen=True)
class SuggestionResponse:
    status: str
    suggestions: tuple[AddressSuggestion, ...] = ()
    message: str = ""
    cached: bool = False


_CACHE: dict[str, tuple[float, SuggestionResponse]] = {}
_last_network_request = 0.0


def _clean_text(value: Any, maximum: int = 200) -> str:
    if not isinstance(value, (str, int)):
        return ""
    text = " ".join(str(value).split()).strip()
    if not text or len(text) > maximum or any(ord(char) < 32 for char in text):
        return ""
    return text


def useful_query(query: str) -> str:
    """Normalize only whitespace; accents and valid punctuation are retained."""

    return " ".join(query.split()).strip() if isinstance(query, str) else ""


def is_eligible_query(query: str) -> bool:
    value = useful_query(query)
    return len("".join(char for char in value if char.isalnum())) >= MIN_QUERY_CHARS and len(value) <= MAX_QUERY_CHARS


def _official_url(query: str) -> str:
    params = urlencode(
        {
            "SingleLine": query,
            "f": "json",
            "maxLocations": str(MAX_SUGGESTIONS),
            "outFields": "Num,Odonyme,Dir,Unite,SufNum,City,ZIP",
        }
    )
    return f"{GEOCODER_URL}?{params}"


def _suggest_url(query: str) -> str:
    """Build the MRNF endpoint designed for suggestions during typing."""

    params = urlencode({"text": query, "f": "json", "maxSuggestions": str(MAX_SUGGESTIONS)})
    return f"{SUGGEST_URL}?{params}"


def _fetch_json(url: str) -> dict[str, Any]:
    """Fetch HTTPS JSON without weakening certificate verification."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "servicescarto.mrnf.gouv.qc.ca":
        raise ValueError("official_host_required")
    # ``requests`` uses the environment certificate bundle with verification on.
    # That is required by the MRNF service in the desktop environment; do not
    # replace it with ``verify=False`` or a custom insecure SSL context.
    response = requests.get(
        url,
        headers={"Accept": "application/json", "User-Agent": "ImmoRadar/1.0"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("invalid_schema")
    return payload


def _candidate_to_suggestion(candidate: Any) -> AddressSuggestion | None:
    if not isinstance(candidate, dict) or not isinstance(candidate.get("attributes"), dict):
        return None
    fields = candidate["attributes"]
    number = _clean_text(fields.get("Num"), 16)
    suffix = _clean_text(fields.get("SufNum"), 16)
    odonym = _clean_text(fields.get("Odonyme"))
    direction = _clean_text(fields.get("Dir"), 16)
    unit = _clean_text(fields.get("Unite"), 30)
    city = _clean_text(fields.get("City"))
    postal_code = normalize_canadian_postal_code(_clean_text(fields.get("ZIP"), 12)) or ""
    street = " ".join(part for part in (f"{number}{suffix}".strip(), odonym, direction) if part)
    if not street:
        # A selected MRNF ``magicKey`` sometimes resolves to a candidate whose
        # attributes contain only City and ZIP.  The official ``address``
        # display field still contains the normalized civic address.  Keep
        # using it instead of rejecting a valid official selection, while
        # removing only an exact trailing city/postal portion that MRNF itself
        # supplied.  This never invents a street, city or postal code.
        street = _clean_text(candidate.get("address"))
        if city:
            city_tail = re.escape(city)
            postal_tail = re.escape(postal_code) if postal_code else r"[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ]\s?\d[ABCEGHJKLMNPRSTVWXYZ]\d"
            street = re.sub(rf"\s*,\s*{city_tail}(?:\s+{postal_tail})?\s*$", "", street, flags=re.IGNORECASE)
        street = re.sub(r"\s+[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ]\s?\d[ABCEGHJKLMNPRSTVWXYZ]\d\s*$", "", street, flags=re.IGNORECASE).strip(" ,")
    if not street:
        return None
    label = " · ".join(part for part in (street, city, postal_code) if part)
    return AddressSuggestion(street=street, city=city, postal_code=postal_code, unit=unit, label=label)


def _suggestion_to_display(item: Any) -> AddressSuggestion | None:
    """Keep only MRNF's display text and opaque lookup key in memory.

    The suggestion endpoint intentionally returns no coordinates.  Its opaque
    key is used only when the person clicks an option; it is never persisted
    in a draft, telemetry, diagnostics or logs.
    """

    if not isinstance(item, dict):
        return None
    label = _clean_text(item.get("text"))
    lookup_key = _clean_text(item.get("magicKey"), 512)
    if not label or not lookup_key or item.get("isCollection") is True:
        return None
    return AddressSuggestion(street="", city="", postal_code="", unit="", label=label, lookup_key=lookup_key)


def _parse_response(payload: dict[str, Any]) -> tuple[AddressSuggestion, ...]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("invalid_schema")
    suggestions: list[AddressSuggestion] = []
    seen: set[tuple[str, str, str, str]] = set()
    for candidate in candidates[:MAX_SUGGESTIONS]:
        suggestion = _candidate_to_suggestion(candidate)
        if suggestion is None:
            continue
        signature = (suggestion.street.casefold(), suggestion.city.casefold(), suggestion.postal_code, suggestion.unit.casefold())
        if signature not in seen:
            seen.add(signature)
            suggestions.append(suggestion)
    return tuple(suggestions)


def _parse_suggest_response(payload: dict[str, Any]) -> tuple[AddressSuggestion, ...]:
    items = payload.get("suggestions")
    if not isinstance(items, list):
        raise ValueError("invalid_schema")
    suggestions: list[AddressSuggestion] = []
    seen: set[str] = set()
    for item in items[:MAX_SUGGESTIONS]:
        suggestion = _suggestion_to_display(item)
        if suggestion is not None and suggestion.label.casefold() not in seen:
            seen.add(suggestion.label.casefold())
            suggestions.append(suggestion)
    return tuple(suggestions)


def clear_suggestion_cache() -> None:
    """Test-only cache reset; the cache never leaves process memory."""

    global _last_network_request
    _CACHE.clear()
    _last_network_request = 0.0


def suggest_addresses(
    query: str,
    consent: bool,
    *,
    fetch_json: Callable[[str], dict[str, Any]] | None = None,
    now: Callable[[], float] = time.monotonic,
) -> SuggestionResponse:
    """Return up to eight suggestions, or a manual-mode response.

    No transport is invoked without consent.  Service failures are purposely
    reduced to a generic status so no address text can reach diagnostics.
    """

    global _last_network_request
    if not consent:
        return SuggestionResponse("consent_required", message="Activez la recherche publique pour obtenir des suggestions.")
    normalized_query = useful_query(query)
    if not is_eligible_query(normalized_query):
        return SuggestionResponse("too_short", message="Saisissez au moins trois caractères utiles pour obtenir des suggestions.")
    cache_key = normalized_query.casefold()
    current_time = now()
    cached = _CACHE.get(cache_key)
    if cached and current_time - cached[0] < CACHE_TTL_SECONDS:
        return SuggestionResponse(cached[1].status, cached[1].suggestions, cached[1].message, cached=True)
    if current_time - _last_network_request < MIN_REQUEST_INTERVAL_SECONDS:
        return SuggestionResponse("rate_limited", message="Suggestions en cours d’actualisation; poursuivez manuellement ou réessayez dans un instant.")
    _last_network_request = current_time
    try:
        # ``suggest`` is the official GeocodeServer operation specifically
        # intended for type-ahead.  Some official deployments temporarily
        # expose it less reliably than ``findAddressCandidates``.  Falling
        # back to that documented operation keeps the same consent, timeout,
        # result limit and privacy guarantees, while returning structured
        # form fields when it succeeds.
        payload = (fetch_json or _fetch_json)(_suggest_url(normalized_query))
        response = SuggestionResponse("ok", _parse_suggest_response(payload))
    except Exception:
        try:
            payload = (fetch_json or _fetch_json)(_official_url(normalized_query))
            response = SuggestionResponse("ok", _parse_response(payload))
        except Exception:  # Network/schema detail is deliberately never retained.
            response = SuggestionResponse("unavailable", message="Le service d’adresses est momentanément indisponible. Vous pouvez poursuivre manuellement.")
    _CACHE[cache_key] = (current_time, response)
    return response


def resolve_freeform_address(
    query: str,
    consent: bool,
    *,
    fetch_json: Callable[[str], dict[str, Any]] | None = None,
    now: Callable[[], float] = time.monotonic,
) -> SuggestionResponse:
    """Resolve a consented, copied address after an explicit user action.

    This is intentionally separate from type-ahead.  It lets the Analyse page
    fill city and postal code from a landing-page hand-off, but never sends an
    address before the person has acknowledged public search.
    """

    if not consent:
        return SuggestionResponse("consent_required", message="Activez la recherche publique avant de révéler les renseignements disponibles.")
    normalized_query = useful_query(query)
    if not is_eligible_query(normalized_query):
        return SuggestionResponse("too_short", message="Saisissez une adresse plus complète, ou poursuivez en mode manuel.")
    cache_key = f"resolve:{normalized_query.casefold()}"
    current_time = now()
    cached = _CACHE.get(cache_key)
    if cached and current_time - cached[0] < CACHE_TTL_SECONDS:
        return SuggestionResponse(cached[1].status, cached[1].suggestions, cached[1].message, cached=True)
    try:
        payload = (fetch_json or _fetch_json)(_official_url(normalized_query))
        response = SuggestionResponse("ok", _parse_response(payload))
    except Exception:
        response = SuggestionResponse("unavailable", message="Le service d’adresses est momentanément indisponible. Vous pouvez poursuivre manuellement.")
    _CACHE[cache_key] = (current_time, response)
    return response


def resolve_suggestion(
    suggestion: AddressSuggestion,
    consent: bool,
    *,
    fetch_json: Callable[[str], dict[str, Any]] | None = None,
) -> AddressSuggestion | None:
    """Resolve an explicitly selected MRNF suggestion into form fields.

    This second, consented request is triggered only by a click.  The opaque
    key is not written anywhere and no raw response data reaches application
    logs or telemetry.
    """

    if not consent or not suggestion.lookup_key or not suggestion.label:
        return None
    params = urlencode(
        {
            "SingleLine": suggestion.label,
            "magicKey": suggestion.lookup_key,
            "f": "json",
            "maxLocations": "1",
            "outFields": "Num,Odonyme,Dir,Unite,SufNum,City,ZIP",
        }
    )
    try:
        payload = (fetch_json or _fetch_json)(f"{GEOCODER_URL}?{params}")
        candidates = _parse_response(payload)
        return candidates[0] if candidates else None
    except Exception:
        return None
