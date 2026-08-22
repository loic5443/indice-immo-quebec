"""Consent and readiness for future Premium email alerts; no automatic delivery."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from providers.brevo_email import BrevoUnavailable, delivery_status, send_email
from repositories.sqlite_repository import SQLiteRepository
from services.entitlements_service import can_use


TEST_ALERT_FINGERPRINT = "brevo-email-test-v1"


def has_alert_email_consent(user_id: int, database_path: Path | str) -> bool:
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        row = connection.execute("SELECT alert_email_consent FROM users WHERE id = ?", (user_id,)).fetchone()
    return bool(row and row[0])


def set_alert_email_consent(user_id: int, consent: bool, database_path: Path | str) -> bool:
    """Persist a separate opt-in. Withdrawal takes effect immediately."""

    timestamp = datetime.now(timezone.utc).isoformat() if consent else None
    try:
        with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
            result = connection.execute(
                "UPDATE users SET alert_email_consent = ?, alert_email_consent_at = ? WHERE id = ?",
                (int(consent), timestamp, user_id),
            )
    except sqlite3.OperationalError:
        # A pre-0023 database can still render the account safely until its
        # normal startup migration runs; no consent is assumed in that case.
        return False
    return result.rowcount == 1


def alert_email_readiness(environment: dict[str, str] | None = None) -> str:
    """Expose only a safe status for the UI, never provider configuration."""

    return delivery_status(environment)


def send_test_alert_email(
    user_id: int,
    database_path: Path | str,
    *,
    environment: dict[str, str] | None = None,
    sender=send_email,
) -> str:
    """Send one explicit, consented test message without logging personal data.

    The delivery log uses a stable technical fingerprint so a double click or a
    Streamlit rerun cannot generate a second test email for the same account.
    """

    if alert_email_readiness(environment) != "ready":
        return "not_ready"

    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        row = connection.execute(
            "SELECT email, plan, role, alert_email_consent FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return "not_found"
        email, plan, role, consent = row
        if not consent:
            return "no_consent"
        if not can_use({"plan": plan, "role": role}, "alerts"):
            return "not_entitled"

        previous = connection.execute(
            "SELECT outcome FROM alert_delivery_log WHERE user_id = ? AND alert_fingerprint = ? AND channel = 'email'",
            (user_id, TEST_ALERT_FINGERPRINT),
        ).fetchone()
        if previous and previous[0] in {"queued", "sent"}:
            return "already_sent"
        if previous:
            connection.execute(
                "UPDATE alert_delivery_log SET outcome = 'queued', created_at = CURRENT_TIMESTAMP "
                "WHERE user_id = ? AND alert_fingerprint = ? AND channel = 'email'",
                (user_id, TEST_ALERT_FINGERPRINT),
            )
        else:
            connection.execute(
                "INSERT INTO alert_delivery_log (user_id, alert_fingerprint, channel, outcome) VALUES (?, ?, 'email', 'queued')",
                (user_id, TEST_ALERT_FINGERPRINT),
            )

    try:
        # The message deliberately includes no dossier, property, or financial
        # information. The recipient is fetched locally and never logged.
        sender(
            str(email),
            "ImmoRadar — test des alertes par courriel",
            "<p>Votre livraison d’alertes ImmoRadar est prête.</p>"
            "<p>Ceci est un test demandé depuis votre compte. Aucune donnée de propriété n’est incluse.</p>",
            environment=environment,
        )
    except (BrevoUnavailable, OSError, ValueError):
        with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
            connection.execute(
                "UPDATE alert_delivery_log SET outcome = 'failed', created_at = CURRENT_TIMESTAMP "
                "WHERE user_id = ? AND alert_fingerprint = ? AND channel = 'email'",
                (user_id, TEST_ALERT_FINGERPRINT),
            )
        return "failed"

    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute(
            "UPDATE alert_delivery_log SET outcome = 'sent', created_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ? AND alert_fingerprint = ? AND channel = 'email'",
            (user_id, TEST_ALERT_FINGERPRINT),
        )
    return "sent"
