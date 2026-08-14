"""Presentation-safe helpers for the guided ImmoValue comparable workspace.

These helpers never estimate a value themselves.  They keep the interface's
admissibility messages, duplicate prevention and conclusion aligned with the
existing deterministic ``domain.immovalue`` engine.
"""

from __future__ import annotations

from datetime import date
import unicodedata
from typing import Any

from domain.immovalue import SubjectProperty, estimate_immovalue


PROPERTY_TYPES = ("", "Maison", "Condo", "Duplex", "Triplex", "Immeuble")


def _normalized(value: object) -> str:
    """Compare declared labels without altering the original user entry."""

    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def comparable_identity(item: dict[str, Any]) -> tuple[str, str, float]:
    """Stable local duplicate key: description, closing date and sale price."""

    return (
        _normalized(item.get("address")),
        str(item.get("sale_date") or "").strip(),
        float(item.get("sale_price") or 0),
    )


def duplicate_comparable(candidate: dict[str, Any], existing: list[dict[str, Any]]) -> bool:
    """Detect only a deterministic duplicate, never a fuzzy address match."""

    identity = comparable_identity(candidate)
    return bool(identity[0] and identity[1] and identity[2] and any(comparable_identity(item) == identity for item in existing))


def comparable_status(item: dict[str, Any]) -> tuple[str, str]:
    """Map engine exclusions to concise, actionable interface statuses."""

    if not item.get("usage_right_confirmed"):
        return "Refusé", "Confirmez votre droit d’utilisation de cette donnée."
    if not item.get("declared_closed_sale"):
        return "Refusé", "Confirmez qu’il s’agit d’une vente conclue."
    required_labels = {
        "address": "adresse ou nom descriptif",
        "sale_date": "date de vente",
        "sale_price": "prix de vente conclu",
        "living_area": "superficie habitable",
        "property_type": "type de propriété",
        "source_declared": "source ou provenance",
    }
    if item.get("guided_entry") and not item.get("city"):
        missing = ["ville"]
    else:
        missing = []
    missing.extend(label for key, label in required_labels.items() if not item.get(key))
    if missing:
        return "Incomplet", "À ajouter : " + ", ".join(missing) + "."
    return "À vérifier", "Les renseignements minimaux sont présents; la similarité sera calculée avec votre propriété."


def reviewed_comparables(subject: SubjectProperty, comparables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose the existing engine decision with a user-facing admissibility label."""

    estimate = estimate_immovalue(subject, comparables)
    reviewed: list[dict[str, Any]] = []
    for item in estimate["comparables"]:
        status, message = comparable_status(item)
        if status == "À vérifier":
            if item["status"] in {"included", "included_with_caution"}:
                status = "Admissible"
                message = item["reason"]
            elif item["status"] == "excluded":
                status = "Refusé"
                message = item["reason"]
        reviewed.append({**item, "display_status": status, "display_reason": message})
    return reviewed


def admissible_count(subject: SubjectProperty, comparables: list[dict[str, Any]]) -> int:
    return sum(item["display_status"] == "Admissible" for item in reviewed_comparables(subject, comparables))


def comparison_conclusion(estimate: dict[str, Any]) -> str:
    """Return a transparent conclusion, never advice or a negotiation guarantee."""

    if not estimate.get("available"):
        return "Données insuffisantes : ajoutez au moins trois comparables admissibles et la superficie de la propriété."
    confidence = estimate.get("confidence", 0)
    confidence_label = "faible" if confidence < 40 else "modérée"
    comparison = estimate.get("asking_comparison")
    gap = estimate.get("asking_gap")
    estimated = estimate.get("estimated_value") or 0
    if comparison and gap is not None and estimated:
        percent = abs(gap) / estimated * 100
        position = {
            "dans la fourchette": "dans la fourchette",
            "supérieur à la fourchette": "au-dessus de la fourchette",
            "inférieur à la fourchette": "sous la fourchette",
        }.get(comparison, comparison)
        return (
            f"Le prix demandé se situe {percent:.0f} % {position} de l’estimation ImmoValue. "
            f"La confiance reste {confidence_label} puisque {estimate.get('used_count', 0)} comparables admissibles sont disponibles."
        )
    return (
        f"L’estimation ImmoValue repose sur {estimate.get('used_count', 0)} comparables admissibles. "
        f"La confiance est {confidence_label}; ajoutez un prix demandé pour le comparer à la fourchette."
    )


def today_iso() -> str:
    """A small test seam for the guided sale-date default."""

    return date.today().isoformat()
