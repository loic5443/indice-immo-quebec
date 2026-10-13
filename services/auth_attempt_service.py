"""Atomic identity-level throttles with hashed identifiers and bounded retention."""
import hashlib
import time
from contextlib import closing

from repositories.sqlite_repository import SQLiteRepository


LIMITS = {"login": (10, 900), "reset": (3, 900)}


def identity_hash(email):
    return hashlib.sha256(str(email).strip().lower().encode()).hexdigest()


def claim_attempt(email, purpose, database_path, now=None):
    limit, window = LIMITS[purpose]
    now = int(time.time() if now is None else now)
    key = identity_hash(email)
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM auth_attempt_windows WHERE window_start < ?", (now - 86400,))
        row = connection.execute("SELECT window_start,attempts FROM auth_attempt_windows WHERE identity_hash=? AND purpose=?", (key, purpose)).fetchone()
        if row is None or now >= row[0] + window:
            connection.execute("INSERT INTO auth_attempt_windows VALUES(?,?,?,1) ON CONFLICT(identity_hash,purpose) DO UPDATE SET window_start=excluded.window_start,attempts=1", (key, purpose, now))
            return True
        if row[1] >= limit:
            return False
        connection.execute("UPDATE auth_attempt_windows SET attempts=attempts+1 WHERE identity_hash=? AND purpose=?", (key, purpose))
        return True


def clear_login_attempts(email, database_path):
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("DELETE FROM auth_attempt_windows WHERE identity_hash=? AND purpose='login'", (identity_hash(email),))
