"""Local SQLite persistence for ImmoRadar's MVP accounts and saved analyses.

Passwords are never stored in plain text.  Each password gets a random salt and
is derived with PBKDF2-HMAC-SHA256 before it reaches SQLite.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parent / "immoradar.db"
PASSWORD_ITERATIONS = 260_000


def _connect(database_path: Path | str = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path | str = DATABASE_PATH) -> None:
    """Create the local schema when it does not exist yet."""
    with closing(_connect(database_path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free', 'premium')),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                property_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                price REAL NOT NULL,
                down_payment REAL NOT NULL,
                rental_income REAL NOT NULL,
                monthly_expenses REAL NOT NULL,
                cash_flow REAL NOT NULL,
                cash_on_cash_return REAL NOT NULL,
                capitalization_rate REAL NOT NULL,
                debt_service_coverage_ratio REAL NOT NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0 CHECK(is_favorite IN (0, 1)),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS analyses_by_user_created
            ON analyses(user_id, created_at DESC);
            """
        )


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return an encoded PBKDF2 hash and its random salt."""
    actual_salt = salt or os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), actual_salt, PASSWORD_ITERATIONS
    )
    return derived_key.hex(), actual_salt.hex()


def validate_registration(name: str, email: str, password: str, confirmation: str) -> list[str]:
    """Validate the account form before any persistence operation."""
    errors: list[str] = []
    if len(name.strip()) < 2:
        errors.append("Veuillez saisir un nom d'au moins 2 caractères.")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        errors.append("Veuillez saisir une adresse courriel valide.")
    if len(password) < 8:
        errors.append("Le mot de passe doit contenir au moins 8 caractères.")
    if password != confirmation:
        errors.append("La confirmation du mot de passe ne correspond pas.")
    return errors


def create_user(
    name: str, email: str, password: str, database_path: Path | str = DATABASE_PATH
) -> tuple[bool, str]:
    """Create a free account, returning a safe message for the interface."""
    password_hash, password_salt = _hash_password(password)
    try:
        with closing(_connect(database_path)) as connection, connection:
            connection.execute(
                """INSERT INTO users (name, email, password_hash, password_salt, plan, created_at)
                VALUES (?, ?, ?, ?, 'free', ?)""",
                (name.strip(), email.strip().lower(), password_hash, password_salt, _now()),
            )
    except sqlite3.IntegrityError:
        return False, "Un compte existe déjà pour cette adresse courriel."
    return True, "Compte créé. Vous pouvez maintenant vous connecter."


def authenticate_user(
    email: str, password: str, database_path: Path | str = DATABASE_PATH
) -> dict[str, Any] | None:
    """Authenticate an account without exposing hashes or salts to the UI."""
    with closing(_connect(database_path)) as connection, connection:
        user = connection.execute(
            "SELECT id, name, email, password_hash, password_salt, plan FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if user is None:
        return None
    attempted_hash, _ = _hash_password(password, bytes.fromhex(user["password_salt"]))
    if not hmac.compare_digest(attempted_hash, user["password_hash"]):
        return None
    return {"id": user["id"], "name": user["name"], "email": user["email"], "plan": user["plan"]}


def count_analyses(user_id: int, database_path: Path | str = DATABASE_PATH) -> int:
    with closing(_connect(database_path)) as connection, connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM analyses WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row["total"])


def save_analysis(
    user_id: int, property_name: str, values: dict[str, float], database_path: Path | str = DATABASE_PATH
) -> int:
    """Save one analysis and bind it permanently to its owner."""
    with closing(_connect(database_path)) as connection, connection:
        cursor = connection.execute(
            """INSERT INTO analyses (
                user_id, property_name, created_at, price, down_payment, rental_income,
                monthly_expenses, cash_flow, cash_on_cash_return, capitalization_rate,
                debt_service_coverage_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                property_name.strip(),
                _now(),
                values["price"],
                values["down_payment"],
                values["rental_income"],
                values["monthly_expenses"],
                values["cash_flow"],
                values["cash_on_cash_return"],
                values["capitalization_rate"],
                values["debt_service_coverage_ratio"],
            ),
        )
    return int(cursor.lastrowid)


def list_analyses(user_id: int, database_path: Path | str = DATABASE_PATH) -> list[dict[str, Any]]:
    """Return only the requested user's analyses, favourites first."""
    with closing(_connect(database_path)) as connection, connection:
        rows = connection.execute(
            "SELECT * FROM analyses WHERE user_id = ? ORDER BY is_favorite DESC, created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_analysis(user_id: int, analysis_id: int, database_path: Path | str = DATABASE_PATH) -> bool:
    """Delete only an analysis owned by the active user."""
    with closing(_connect(database_path)) as connection, connection:
        cursor = connection.execute(
            "DELETE FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id)
        )
    return cursor.rowcount == 1


def toggle_favorite(user_id: int, analysis_id: int, database_path: Path | str = DATABASE_PATH) -> bool:
    """Toggle a favourite only when the analysis belongs to the supplied user."""
    with closing(_connect(database_path)) as connection, connection:
        cursor = connection.execute(
            """UPDATE analyses
            SET is_favorite = CASE is_favorite WHEN 1 THEN 0 ELSE 1 END
            WHERE id = ? AND user_id = ?""",
            (analysis_id, user_id),
        )
    return cursor.rowcount == 1


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
