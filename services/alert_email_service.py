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
    """Return a safe default while a temporary or pre-migration DB is absent.

    Account rendering must never fail merely because an isolated UI test (or a
    startup edge case) has no database available yet.  Absence always means no
    consent; it never enables email delivery.
    """

    try:
        with closing(SQLiteRepository(database_path)._connect()) as connection:
            row = connection.execute("SELECT alert_email_consent FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.Error:
        return False
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


def alert_email_delivery_status(
    user_id: int,
    database_path: Path | str,
    *,
    environment: dict[str, str] | None = None,
) -> dict[str, str | bool | None]:
    """Return a safe, owner-scoped delivery summary for the account screen.

    The summary deliberately exposes only the opt-in, a categorical provider
    readiness value and the latest outcome timestamp.  It never returns an
    email address, alert fingerprint, property, financial value or provider
    configuration.
    """

    latest_outcome: str | None = None
    latest_at: str | None = None
    try:
        with closing(SQLiteRepository(database_path)._connect()) as connection:
            row = connection.execute(
                """SELECT outcome,created_at FROM alert_delivery_log
                WHERE user_id=? AND channel='email' ORDER BY id DESC LIMIT 1""",
                (int(user_id),),
            ).fetchone()
    except sqlite3.OperationalError:
        row = None
    if row:
        latest_outcome, latest_at = str(row[0]), str(row[1])
    return {
        "consent": has_alert_email_consent(int(user_id), database_path),
        "readiness": alert_email_readiness(environment),
        "latest_outcome": latest_outcome,
        "latest_at": latest_at,
    }


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
