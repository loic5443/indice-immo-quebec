"""Consent-first suggestions from the official MRNF Adresses Québec geocoder.

Only the request needed by the user is sent to MRNF after explicit consent.
Coordinates, match scores and the raw payload are intentionally discarded and
are never passed to telemetry, diagnostics, drafts or application logs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Any, Callable
from urllib.parse import urlencode, urlparse

import requests

from domain.address import normalize_canadian_postal_code


GEOCODER_URL = (
    "https://servicescarto.mrnf.gouv.qc.ca/pes/rest/services/"
    "Territoire/Adresse_Geocodage/GeocodeServer/findAddressCandidates"
)
SOURCE_ID = "mrnf_adresses_quebec_geocoder"
SOURCE_LABEL = "MRNF — Adresses Québec"
MIN_QUERY_CHARS = 4
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

    def to_dict(self) -> dict[str, str]:
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
        return None
    label = " · ".join(part for part in (street, city, postal_code) if part)
    return AddressSuggestion(street=street, city=city, postal_code=postal_code, unit=unit, label=label)


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
        return SuggestionResponse("too_short", message="Saisissez au moins quatre caractères utiles pour obtenir des suggestions.")
    cache_key = normalized_query.casefold()
    current_time = now()
    cached = _CACHE.get(cache_key)
    if cached and current_time - cached[0] < CACHE_TTL_SECONDS:
        return SuggestionResponse(cached[1].status, cached[1].suggestions, cached[1].message, cached=True)
    if current_time - _last_network_request < MIN_REQUEST_INTERVAL_SECONDS:
        return SuggestionResponse("rate_limited", message="Suggestions en cours d’actualisation; poursuivez manuellement ou réessayez dans un instant.")
    _last_network_request = current_time
    try:
        payload = (fetch_json or _fetch_json)(_official_url(normalized_query))
        response = SuggestionResponse("ok", _parse_response(payload))
    except Exception:  # Network/schema detail is deliberately never retained.
        response = SuggestionResponse("unavailable", message="Le service d’adresses est momentanément indisponible. Vous pouvez poursuivre manuellement.")
    _CACHE[cache_key] = (current_time, response)
    return response
