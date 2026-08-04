"""Single-source-of-truth state for the consented public-address lookup form.

The UI deliberately keeps this state separate from Streamlit widget keys.  A
widget is only a temporary editor; a submitted ``AddressFormState`` is the
canonical record used for validation, local drafts and the official lookup.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from domain.address import AddressValidationError, QuebecAddress, normalize_address


ADDRESS_FIELDS = ("street", "city", "postal", "unit", "consent")


@dataclass(frozen=True)
class AddressFormState:
    """Canonical submission plus the exact values that should be shown again."""

    values: dict[str, Any]
    address: QuebecAddress | None
    errors: dict[str, str]
    # Only non-sensitive, local provenance is kept here.  It allows an
    # official role record that does not publish a postal code to be resumed
    # without turning an absence in the source into a validation error.
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return self.address is not None and not self.errors


def empty_address_form_state() -> AddressFormState:
    return AddressFormState(
        values={"street": "", "city": "", "postal": "", "unit": "", "consent": False},
        address=None,
        errors={},
    )


def submit_address_form(
    street: str, city: str, postal: str, unit: str = "", consent: bool = False,
    *, allow_missing_postal: bool = False, metadata: dict[str, Any] | None = None,
) -> AddressFormState:
    """Validate the values submitted in one event and return their canonical form.

    The address text remains the original submitted text.  The postal code is
    formatted only after successful validation, so the next render displays the
    same canonical state that will be used for the lookup.
    """

    values = {
        "street": street if isinstance(street, str) else "",
        "city": city if isinstance(city, str) else "",
        "postal": postal if isinstance(postal, str) else "",
        "unit": unit if isinstance(unit, str) else "",
        "consent": bool(consent),
    }
    try:
        address = normalize_address(
            values["street"], values["city"], values["postal"], values["unit"],
            allow_missing_postal=allow_missing_postal,
        )
    except AddressValidationError as error:
        return AddressFormState(values=values, address=None, errors={error.field: str(error)}, metadata=dict(metadata or {}))

    # Keep the copied map address intact while preserving the structured street
    # separately in ``address``.  This prevents a visual/validated mismatch.
    display_values = {
        **values,
        "street": address.original_street,
        "city": address.city,
        "postal": address.postal_code,
        "unit": address.unit,
    }
    return AddressFormState(values=display_values, address=address, errors={}, metadata=dict(metadata or {}))


def serialize_address_form(state: AddressFormState) -> dict[str, Any]:
    """Return JSON-safe local-draft content; never use it for telemetry."""

    return {
        "values": state.values,
        "address": asdict(state.address) if state.address else None,
        "errors": state.errors,
        "metadata": state.metadata,
    }


def restore_address_form(payload: Any) -> AddressFormState:
    """Restore a valid local draft without trusting a stale validation error."""

    if not isinstance(payload, dict):
        return empty_address_form_state()
    values = payload.get("values")
    if not isinstance(values, dict):
        return empty_address_form_state()
    restored = submit_address_form(
        values.get("street", ""),
        values.get("city", ""),
        values.get("postal", ""),
        values.get("unit", ""),
        values.get("consent", False),
        allow_missing_postal=bool((payload.get("metadata") or {}).get("postal_optional", False)),
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None,
    )
    # A malformed or obsolete draft is shown for correction, never accepted.
    return restored
