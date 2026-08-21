"""Local-only Premium interest preferences, always scoped to one account."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

from repositories.sqlite_repository import SQLiteRepository


def has_premium_interest(user_id: int, database_path: Path | str) -> bool:
    """Return the account's local choice without exposing any other account."""

    with closing(SQLiteRepository(database_path)._connect()) as connection:
        row = connection.execute(
            "SELECT 1 FROM premium_interest WHERE user_id = ? AND consent = 1", (user_id,),
        ).fetchone()
    return row is not None


def set_premium_interest(user_id: int, consent: bool, database_path: Path | str) -> None:
    """Store or remove a local interest preference; no external contact is made."""

    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        if consent:
            connection.execute(
                "INSERT INTO premium_interest(user_id, consent) VALUES (?, 1) "
                "ON CONFLICT(user_id) DO UPDATE SET consent = 1",
                (user_id,),
            )
        else:
            connection.execute("DELETE FROM premium_interest WHERE user_id = ?", (user_id,))
