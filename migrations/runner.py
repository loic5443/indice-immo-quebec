"""Transactional SQLite migrations, serialized across app and worker processes."""
import sqlite3
from contextlib import closing
from pathlib import Path


MIGRATIONS_DIRECTORY = Path(__file__).resolve().parent


def _statements(sql):
    # SQLite itself decides completeness, including semicolons inside strings
    # and trigger bodies. execute() preserves the outer transaction, unlike
    # executescript(), which would implicitly commit it first.
    buffer = ""
    for character in sql:
        buffer += character
        if character == ";" and sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ""
    if buffer.strip():
        yield buffer


def apply_migrations(database_path: Path | str) -> list[str]:
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(database_path, timeout=30)) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        connection.commit()
        newly_applied = []
        for file in sorted(MIGRATIONS_DIRECTORY.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            version = file.stem.split("_", maxsplit=1)[0]
            try:
                connection.execute("BEGIN IMMEDIATE")
                if connection.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone():
                    connection.rollback()
                    continue
                for statement in _statements(file.read_text(encoding="utf-8")):
                    connection.execute(statement)
                connection.execute("INSERT INTO schema_migrations(version) VALUES(?)", (version,))
                connection.commit()
                newly_applied.append(version)
            except Exception:
                connection.rollback()
                raise
    database_path.chmod(0o600)
    return newly_applied


def applied_migrations(database_path: Path | str) -> list[str]:
    with closing(sqlite3.connect(database_path)) as connection:
        return [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
