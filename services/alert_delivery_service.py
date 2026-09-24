"""Deliver factual tracked-dossier alerts without putting dossier data in email.

The alert rules remain in :mod:`services.alert_service`. This module only
claims an alert once, sends a generic opt-in notification, and stores a
one-way technical fingerprint. It never stores an address, a financial value,
or an alert message in the delivery log.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import sqlite3
from typing import Callable

from providers.brevo_email import BrevoUnavailable, send_email
from repositories.sqlite_repository import SQLiteRepository
from services.alert_email_service import alert_email_readiness
from services.alert_service import build_calculable_alerts
from services.dossier_tracking_service import filter_tracked_analyses
from services.entitlements_service import can_use


AlertSender = Callable[..., None]


@dataclass(frozen=True)
class AlertDeliveryResult:
    """A safe aggregate for the UI and the local worker."""

    status: str
    available: int = 0
    claimed: int = 0
    delivered: int = 0


def _fingerprint(user_id: int, alert: dict) -> str:
    """Create an irreversible, stable key for one saved alert occurrence."""

    basis = "|".join((
        "alert-email-v1",
        str(int(user_id)),
        str(int(alert["analysis_id"])),
        str(alert["kind"]),
        str(alert.get("created_at") or ""),
    ))
    return sha256(basis.encode("utf-8")).hexdigest()


def _claim_alerts(user_id: int, alerts: list[dict], database_path: Path | str) -> list[str]:
    """Claim new alerts atomically so reruns and double clicks cannot resend."""

    claimed: list[str] = []
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        for alert in alerts:
            fingerprint = _fingerprint(user_id, alert)
            try:
                connection.execute(
                    "INSERT INTO alert_delivery_log (user_id, alert_fingerprint, channel, outcome) "
                    "VALUES (?, ?, 'email', 'queued')",
                    (user_id, fingerprint),
                )
            except sqlite3.IntegrityError:
                # A delivered, failed, or in-flight occurrence is never
                # automatically resent. This protects recipients from
                # duplicates when Streamlit reruns.
                continue
            claimed.append(fingerprint)
    return claimed


def _finish_claims(user_id: int, fingerprints: list[str], outcome: str, database_path: Path | str) -> None:
    if not fingerprints:
        return
    placeholders = ", ".join("?" for _ in fingerprints)
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute(
            f"UPDATE alert_delivery_log SET outcome = ?, created_at = CURRENT_TIMESTAMP "
            f"WHERE user_id = ? AND channel = 'email' AND alert_fingerprint IN ({placeholders})",
            (outcome, user_id, *fingerprints),
        )


def _eligible_user(user_id: int, database_path: Path | str) -> dict | None:
    """Reload consent and rights from SQLite, never from a Streamlit session."""

    with closing(SQLiteRepository(database_path)._connect()) as connection:
        row = connection.execute(
            "SELECT id, email, plan, role, alert_email_consent FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    user = dict(row)
    if not bool(user["alert_email_consent"]) or not can_use(user, "alerts"):
        return None
    return user


def _generic_email_content(alert_count: int) -> tuple[str, str]:
    """Keep emails useful without disclosing a dossier in an inbox preview."""

    plural = "s" if alert_count > 1 else ""
    subject = "ImmoRadar — une alerte est disponible"
    content = (
        "<p>Une ou plusieurs alertes vérifiables sont disponibles dans votre espace ImmoRadar.</p>"
        f"<p>{alert_count} nouvelle{plural} alerte{plural} a été détectée{plural} dans vos dossiers suivis.</p>"
        "<p>Connectez-vous à ImmoRadar pour consulter le détail, les sources et les limites. "
        "Ce courriel ne contient aucune adresse ni donnée financière.</p>"
    )
    return subject, content


def deliver_alerts_for_user(
    user_id: int,
    database_path: Path | str,
    *,
    environment: dict[str, str] | None = None,
    sender: AlertSender = send_email,
) -> AlertDeliveryResult:
    """Send at most one generic digest for newly calculable alerts of one owner.

    Saved analyses and tracked choices are reloaded in the owner's scope. No
    alert is produced from guessed data, no delivery occurs without the
    separate opt-in, and no content is persisted outside private snapshots.
    """

    if alert_email_readiness(environment) != "ready":
        return AlertDeliveryResult("not_ready")

    user = _eligible_user(int(user_id), database_path)
    if user is None:
        return AlertDeliveryResult("not_eligible")

    repository = SQLiteRepository(database_path)
    analyses = repository.list_analyses(int(user_id))
    tracked = filter_tracked_analyses(int(user_id), analyses, database_path)
    alerts = build_calculable_alerts(tracked)
    if not alerts:
        return AlertDeliveryResult("no_alert")

    fingerprints = _claim_alerts(int(user_id), alerts, database_path)
    if not fingerprints:
        return AlertDeliveryResult("already_processed", available=len(alerts))

    subject, content = _generic_email_content(len(fingerprints))
    try:
        sender(str(user["email"]), subject, content, environment=environment)
    except (BrevoUnavailable, OSError, ValueError):
        _finish_claims(int(user_id), fingerprints, "failed", database_path)
        return AlertDeliveryResult("failed", available=len(alerts), claimed=len(fingerprints))

    _finish_claims(int(user_id), fingerprints, "sent", database_path)
    return AlertDeliveryResult(
        "sent", available=len(alerts), claimed=len(fingerprints), delivered=len(fingerprints),
    )


def deliver_alerts_for_all_users(
    database_path: Path | str,
    *,
    environment: dict[str, str] | None = None,
    sender: AlertSender = send_email,
) -> list[AlertDeliveryResult]:
    """Run the safe local worker without exposing account identities."""

    repository = SQLiteRepository(database_path)
    return [
        deliver_alerts_for_user(user_id, database_path, environment=environment, sender=sender)
        for user_id in repository.alert_delivery_user_ids()
    ]
