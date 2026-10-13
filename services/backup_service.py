"""Consistent SQLite backups written privately, without copying live DB files."""
import hashlib
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


class BackupError(ValueError):
    pass


def verify_backup(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise BackupError("La sauvegarde est introuvable.")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BackupError("La sauvegarde SQLite est invalide.")
        if connection.execute("PRAGMA foreign_key_check").fetchone():
            raise BackupError("La sauvegarde contient une référence invalide.")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"schema_migrations", "users", "analyses"}.issubset(tables):
            raise BackupError("Ce fichier n’est pas une base ImmoRadar reconnue.")
        version = connection.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1").fetchone()
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"integrity": "ok", "schema_version": version[0] if version else None, "sha256": digest.hexdigest()}


def backup_database(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or source == destination or destination.exists():
        raise BackupError("La source doit exister et la destination doit être un nouveau fichier.")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".immoradar-backup-", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as reader, closing(sqlite3.connect(temporary)) as writer:
            reader.backup(writer)
        metadata = verify_backup(temporary)
        os.chmod(temporary, 0o600)
        # Exclusive destination creation avoids replacing an existing backup.
        os.link(temporary, destination)
        return metadata
    finally:
        temporary.unlink(missing_ok=True)
