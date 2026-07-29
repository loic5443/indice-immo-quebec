"""Experimental, deterministic comparable-sales estimate from user-declared inputs only."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Any


IMMOVALUE_VERSION = "ImmoValue 0.1.0-experimental"
SIMILARITY_WEIGHTS = {"type_units": 30, "area": 25, "distance": 15, "year_condition": 10, "land": 10, "configuration": 5, "quality": 5}


@dataclass(frozen=True)
class SubjectProperty:
    name: str = ""
    property_type: str = ""
    units: int | None = None
    living_area: float | None = None
    land_area: float | None = None
    year_built: int | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    parking: int | None = None
    garage: bool | None = None
    condition: str = ""
    reference_date: str = ""
    asking_price: float | None = None
    municipal_assessment: float | None = None
    assessment_year: int | None = None
    renovations: str = ""
    notes: str = ""


def _ratio_score(difference: float, threshold: float) -> float:
    return max(0.0, 100 * (1 - difference / threshold))


def evaluate_comparable(subject: SubjectProperty, comparable: dict[str, Any]) -> dict[str, Any]:
    """Classify an explicitly declared closed sale and expose every scoring decision."""
    reasons, available, earned = [], 0.0, 0.0
    if not comparable.get("usage_right_confirmed"):
        return {**comparable, "status": "excluded", "reason": "Droit d'utilisation non confirmé.", "similarity": 0.0}
    if not comparable.get("declared_closed_sale"):
        return {**comparable, "status": "excluded", "reason": "Une annonce active ne peut pas être une vente conclue.", "similarity": 0.0}
    required = ("address", "sale_date", "sale_price", "living_area", "property_type")
    missing = [key for key in required if not comparable.get(key)]
    if missing:
        return {**comparable, "status": "excluded", "reason": "Données minimales manquantes : " + ", ".join(missing), "similarity": 0.0}
    if subject.property_type:
        available += 30
        if comparable["property_type"] == subject.property_type and (not subject.units or comparable.get("units") == subject.units): earned += 30
        else: reasons.append("type ou nombre d'unités différent")
    if subject.living_area and comparable.get("living_area"):
        available += 25; earned += 25 * _ratio_score(abs(comparable["living_area"] - subject.living_area) / subject.living_area, .35) / 100
    if comparable.get("distance_km") is not None:
        available += 15; earned += 15 * _ratio_score(float(comparable["distance_km"]), 10) / 100
    if subject.year_built and comparable.get("year_built"):
        available += 10; earned += 10 * _ratio_score(abs(comparable["year_built"] - subject.year_built), 50) / 100
    if subject.land_area and comparable.get("land_area"):
        available += 10; earned += 10 * _ratio_score(abs(comparable["land_area"] - subject.land_area) / subject.land_area, .50) / 100
    if subject.bedrooms is not None and comparable.get("bedrooms") is not None:
        available += 5; earned += 5 if comparable["bedrooms"] == subject.bedrooms else 2.5
    available += 5; earned += 5 if comparable.get("source_declared") else 0
    similarity = round(earned / available * 100, 1) if available else 0.0
    status = "included" if similarity >= 65 else "included_with_caution" if similarity >= 40 else "excluded"
    if status == "excluded": reasons.append("similarité insuffisante")
    return {**comparable, "status": status, "reason": "; ".join(reasons) or "Comparable suffisamment similaire selon les renseignements déclarés.", "similarity": similarity,
            "price_per_area": round(comparable["sale_price"] / comparable["living_area"], 2), "manual_adjustment": float(comparable.get("manual_adjustment") or 0)}


def _weighted_median(values: list[tuple[float, float]]) -> float:
    total = sum(weight for _, weight in values); running = 0.0
    for value, weight in sorted(values):
        running += weight
        if running >= total / 2: return value
    return values[-1][0]


def estimate_immovalue(subject: SubjectProperty, comparables: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = [evaluate_comparable(subject, item) for item in comparables]
    usable = [item for item in reviewed if item["status"] in ("included", "included_with_caution")]
    base = {"version": IMMOVALUE_VERSION, "comparables": reviewed, "method": "Médiane pondérée des prix par superficie des ventes déclarées admissibles.", "limitations": ["Expérimental : aucune validation historique n'est disponible.", "Comparables et droits d'utilisation déclarés par l'utilisateur."], "subject": asdict(subject)}
    if len(usable) < 3 or not subject.living_area:
        return {**base, "available": False, "confidence": 0, "confidence_factors": ["Au moins trois comparables admissibles et une superficie du sujet sont requis."], "missing_data": ["Comparables admissibles ou superficie du sujet insuffisants."]}
    values = [(item["price_per_area"] * subject.living_area + item["manual_adjustment"], max(item["similarity"], 1)) for item in usable]
    central = _weighted_median(values); raw_values = [value for value, _ in values]
    dispersion = (max(raw_values) - min(raw_values)) / central if central else 1
    average_similarity = sum(item["similarity"] for item in usable) / len(usable)
    declared_cap = 65
    confidence = min(declared_cap, round(25 + min(len(usable), 6) * 5 + average_similarity * .25 - dispersion * 50 - sum(bool(item["manual_adjustment"]) for item in usable) * 5))
    margin = max(.10, .08 + dispersion / 2 + (3 / len(usable) - 0.5) * .04 + sum(bool(item["manual_adjustment"]) for item in usable) * .02)
    central = round(central / 1000) * 1000
    low, high = round(central * (1 - margin) / 1000) * 1000, round(central * (1 + margin) / 1000) * 1000
    asking = subject.asking_price
    comparison = None if not asking else ("inférieur à la fourchette" if asking < low else "supérieur à la fourchette" if asking > high else "dans la fourchette")
    return {**base, "available": True, "estimated_value": central, "low": low, "high": high, "median": round(median(raw_values) / 1000) * 1000, "dispersion_pct": round(dispersion * 100, 1), "unit_price": round(central / subject.living_area, 2), "used_count": len(usable), "confidence": max(0, confidence), "confidence_factors": [f"{len(usable)} comparables admissibles.", f"Similarité moyenne : {average_similarity:.0f} / 100.", "Confiance plafonnée à 65 / 100 : données déclarées non vérifiées.", "Marge minimale prudente de 10 % sans backtesting."], "missing_data": [], "asking_comparison": comparison, "asking_gap": None if not asking else round(asking - central, -3)}
