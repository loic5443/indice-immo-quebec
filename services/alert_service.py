"""Build factual in-app alerts from a user's immutable saved-analysis snapshots."""

from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from datetime import date
from typing import Any


def _json_object(raw: str | None, fallback: Any) -> Any:
    try:
        value = json.loads(raw or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
    return value if isinstance(value, type(fallback)) else fallback


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _property_key(analysis: dict[str, Any]) -> str:
    """Only exact normalized dossier names are grouped; similar names are not guessed."""
    text = unicodedata.normalize("NFKD", str(analysis.get("property_name") or ""))
    return "".join(char for char in text.lower() if not unicodedata.combining(char)).strip()


def _immovalue(analysis: dict[str, Any]) -> dict[str, Any]:
    value = _json_object(analysis.get("immovalue_json"), {})
    return value if value.get("available") else {}


def _role(analysis: dict[str, Any]) -> dict[str, Any]:
    return _json_object(analysis.get("official_role_snapshot_json"), {})


def _rate_plus_one_cash_flow(analysis: dict[str, Any]) -> float | None:
    resilience = _json_object(analysis.get("resilience_json"), {})
    for item in resilience.get("tests", []) if isinstance(resilience, dict) else []:
        if isinstance(item, dict) and item.get("name") == "Taux +1 point":
            financial = item.get("financial")
            if isinstance(financial, dict):
                return _number(financial.get("cash_flow_monthly"))
    return None


def _mortgage_renewal_date(analysis: dict[str, Any]) -> date | None:
    """Read only an explicitly saved ISO date; invalid or absent values stay absent."""

    financial = _json_object(analysis.get("financial_inputs_json"), {})
    value = financial.get("mortgage_renewal_date") if isinstance(financial, dict) else None
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _money(value: float) -> str:
    return f"{value:,.0f} $".replace(",", " ")


def _alert(kind: str, severity: str, title: str, detail: str, analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "severity": severity,
        "title": title,
        "detail": detail,
        "analysis_id": int(analysis["id"]),
        "property_name": analysis.get("property_name") or "Dossier sans nom",
        "created_at": analysis.get("created_at"),
    }


def build_calculable_alerts(analyses: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    """Return alerts supported by saved data only; this never refreshes or guesses.

    The caller supplies an owner-scoped list. No address, financial value or alert
    payload is transmitted: these are ephemeral messages displayed in-app only.
    """
    today = today or date.today()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for analysis in analyses:
        key = _property_key(analysis)
        if key:
            grouped[key].append(analysis)

    alerts: list[dict[str, Any]] = []
    for history in grouped.values():
        ordered = sorted(history, key=lambda item: (str(item.get("created_at") or ""), int(item.get("id") or 0)), reverse=True)
        latest = ordered[0]
        if len(ordered) >= 2:
            previous = ordered[1]
            latest_value, previous_value = _immovalue(latest), _immovalue(previous)
            latest_estimate = _number(latest_value.get("estimated_value"))
            previous_estimate = _number(previous_value.get("estimated_value"))
            latest_confidence = _number(latest_value.get("confidence"))
            previous_confidence = _number(previous_value.get("confidence"))
            if (
                latest_estimate is not None and previous_estimate is not None
                and latest_confidence is not None and previous_confidence is not None
                and min(latest_confidence, previous_confidence) >= 40 and previous_estimate > 0
            ):
                change = latest_estimate - previous_estimate
                if abs(change) >= 1:
                    alerts.append(_alert(
                        "immovalue_change", "info", "ImmoValue a changé",
                        f"L’estimation expérimentale a varié de {_money(abs(change))} ({change / previous_estimate:+.1%}) entre les deux derniers instantanés. Cette variation vient des comparables et hypothèses sauvegardés.",
                        latest,
                    ))

            latest_role, previous_role = _role(latest), _role(previous)
            latest_total = _number(latest_role.get("total_value"))
            previous_total = _number(previous_role.get("total_value"))
            if latest_total is not None and previous_total is not None and latest_total != previous_total and previous_total > 0:
                change = latest_total - previous_total
                alerts.append(_alert(
                    "municipal_role_change", "info", "La valeur au rôle municipal a changé",
                    f"Le repère fiscal sauvegardé a varié de {_money(abs(change))} ({change / previous_total:+.1%}) entre les deux derniers rôles disponibles. Ce n’est pas une estimation de valeur marchande.",
                    latest,
                ))

        current_cash_flow = _number(latest.get("cash_flow"))
        stressed_cash_flow = _rate_plus_one_cash_flow(latest)
        if current_cash_flow is not None and stressed_cash_flow is not None and current_cash_flow >= 0 > stressed_cash_flow:
            alerts.append(_alert(
                "rate_sensitivity", "important", "Une hausse de taux fragilise le flux mensuel",
                f"Dans le scénario sauvegardé « Taux +1 point », le flux passe de {_money(current_cash_flow)} à {_money(stressed_cash_flow)} par mois. C’est un test de sensibilité, pas une prévision de taux.",
                latest,
            ))

        renewal_date = _mortgage_renewal_date(latest)
        if renewal_date:
            days_remaining = (renewal_date - today).days
            if 0 <= days_remaining <= 180:
                severity = "important" if days_remaining <= 90 else "info"
                alerts.append(_alert(
                    "mortgage_renewal", severity, "Renouvellement hypothécaire à préparer",
                    f"La date de renouvellement que vous avez saisie est dans {days_remaining} jour(s), le {renewal_date.isoformat()}. Vérifiez vos options de financement; ce rappel ne prévoit pas l’évolution des taux.",
                    latest,
                ))

    priority = {"important": 0, "info": 1}
    return sorted(alerts, key=lambda item: (priority[item["severity"]], str(item["created_at"])))
