"""Small dependency-free migration runner for ImmoRadar's local SQLite database."""

import sqlite3
from contextlib import closing
from pathlib import Path


MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent


def apply_migrations(database_path: Path | str) -> list[str]:
    """Apply each unapplied SQL migration once, in filename order."""
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"""
        )
        applied = {
            row[0] for row in connection.execute("SELECT version FROM schema_migrations")
        }
        newly_applied: list[str] = []
        for migration_file in sorted(MIGRATIONS_DIRECTORY.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            version = migration_file.stem.split("_", maxsplit=1)[0]
            if version in applied:
                continue
            connection.executescript(migration_file.read_text(encoding="utf-8"))
            connection.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
            newly_applied.append(version)
    return newly_applied


def applied_migrations(database_path: Path | str) -> list[str]:
    """List migration versions already recorded for diagnostics and tests."""
    with closing(sqlite3.connect(database_path)) as connection:
        return [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
