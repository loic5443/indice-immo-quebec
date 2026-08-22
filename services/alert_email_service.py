"""Consent and readiness for future Premium email alerts; no automatic delivery."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from providers.brevo_email import delivery_status
from repositories.sqlite_repository import SQLiteRepository


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
