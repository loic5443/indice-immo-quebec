"""Controlled, consent-first synchronization of one official Quebec role.

This service never receives or stores an address.  It receives only a
municipality name already returned by an explicitly selected public address,
resolves it exactly in the official MAMH index, and imports one territory.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
import unicodedata
import urllib.error
import urllib.request
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from services.diagnostics_service import source_enabled
from services.quebec_role_importer import import_role_xml
from services.quebec_role_sync import INDEX_URL, parse_index, validate_xml


SOURCE_ID = "mamh_quebec_assessment_rolls"
OFFICIAL_HOSTS = frozenset({"mamh.gouv.qc.ca", "www.mamh.gouv.qc.ca"})
MAX_BYTES = 20_000_000
TIMEOUT_SECONDS = 15
COOLDOWN_SECONDS = 300
LOCK_TTL_SECONDS = 300
_PROCESS_LOCK = threading.Lock()


@dataclass(frozen=True)
class AutoSyncResult:
    status: str
    message: str
    territory_code: str = ""
    imported_units: int = 0
    size_bytes: int = 0
    source_version: str = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp() -> str:
    return _now().isoformat()


def _municipality_key(value: str) -> str:
    """Normalize typography only; an index match remains exact and deterministic."""

    text = " ".join(str(value or "").split()).casefold()
    text = unicodedata.normalize("NFD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def _canonical_mamh_url(url: str) -> str:
    """Use MAMH's canonical HTTPS hostname without following a redirect."""

    return str(url).replace("https://mamh.gouv.qc.ca/", "https://www.mamh.gouv.qc.ca/", 1)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # pragma: no cover - urllib dispatch
        return None


def _official_download(url: str, maximum: int = MAX_BYTES) -> bytes:
    """Read one MAMH document with a bounded size, timeout and no redirects."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise ValueError("official_host_required")
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "ImmoRadar/1.0 official-data"})
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.geturl() != url:
                raise ValueError("redirect_refused")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > maximum:
                raise ValueError("official_file_too_large")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum:
                    raise ValueError("official_file_too_large")
                chunks.append(chunk)
            return b"".join(chunks)
    except urllib.error.HTTPError as error:
        raise ValueError("official_http_error") from error
    except urllib.error.URLError as error:
        raise ValueError("official_network_unavailable") from error


def _record_history(connection: sqlite3.Connection, territory: str, action: str, outcome: str, detail: str = "", *, checksum: str | None = None, units: int | None = None) -> None:
    """Store only categorical operational metadata—never municipality or address text."""

    connection.execute(
        "INSERT INTO role_sync_history(territory_code,action,outcome,checksum,imported_units,detail) VALUES(?,?,?,?,?,?)",
        (territory, action, outcome, checksum, units, detail[:120]),
    )


def _record_attempt(connection: sqlite3.Connection, territory: str, status: str, error_code: str = "") -> None:
    connection.execute(
        """INSERT INTO role_auto_sync_attempts(territory_code,status,last_attempt_at,last_success_at,error_code)
        VALUES(?,?,?,?,?)
        ON CONFLICT(territory_code) DO UPDATE SET status=excluded.status,last_attempt_at=excluded.last_attempt_at,
        last_success_at=CASE WHEN excluded.status='success' THEN excluded.last_attempt_at ELSE role_auto_sync_attempts.last_success_at END,
        error_code=excluded.error_code""",
        (territory, status, _stamp(), _stamp() if status == "success" else None, error_code or None),
    )


def _index_entry(database_path: Path | str, municipality: str) -> dict | None:
    key = _municipality_key(municipality)
    if not key:
        return None
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT territory_code,municipality,source_url,source_updated_at FROM role_index_entries").fetchall()
    matches = [dict(row) for row in rows if _municipality_key(row["municipality"]) == key]
    return matches[0] if len(matches) == 1 else None


def _refresh_index_if_empty(database_path: Path | str, index_fetcher) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        existing = connection.execute("SELECT COUNT(*) FROM role_index_entries").fetchone()[0]
    if existing:
        return
    rows = parse_index(index_fetcher(INDEX_URL))
    now = _stamp()
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.executemany(
            "INSERT OR REPLACE INTO role_index_entries(territory_code,municipality,source_url,source_updated_at,index_synced_at) VALUES(?,?,?,?,?)",
            [(row["territory_code"], row["municipality"], row["url"], row["updated_at"], now) for row in rows],
        )
        _record_history(connection, "*", "public_index_refresh", "success", "official_index")


def resolve_official_territory(database_path: Path | str, municipality: str, *, index_fetcher=_official_download) -> dict | None:
    """Resolve one municipality only through an exact official-index entry."""

    entry = _index_entry(database_path, municipality)
    if entry is None:
        _refresh_index_if_empty(database_path, index_fetcher)
        entry = _index_entry(database_path, municipality)
    return entry


def _territory_is_available(database_path: Path | str, territory: str) -> bool:
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """SELECT imported.territory_code FROM role_territory_imports imported
            LEFT JOIN role_territory_settings settings ON settings.territory_code=imported.territory_code
            WHERE imported.territory_code=? AND COALESCE(settings.enabled,1)=1""",
            (territory,),
        ).fetchone()
    return bool(row)


def _territory_is_disabled(database_path: Path | str, territory: str) -> bool:
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute("SELECT enabled FROM role_territory_settings WHERE territory_code=?", (territory,)).fetchone()
    return bool(row and not row[0])


def _cooling_down(database_path: Path | str, territory: str) -> bool:
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute("SELECT status,last_attempt_at FROM role_auto_sync_attempts WHERE territory_code=?", (territory,)).fetchone()
    if not row or row[0] == "success":
        return False
    try:
        return _now() - datetime.fromisoformat(row[1]) < timedelta(seconds=COOLDOWN_SECONDS)
    except (TypeError, ValueError):
        return False


def _acquire_lock(database_path: Path | str, territory: str) -> bool:
    with closing(sqlite3.connect(database_path)) as connection, connection:
        existing = connection.execute("SELECT acquired_at FROM role_auto_sync_locks WHERE territory_code=?", (territory,)).fetchone()
        if existing:
            try:
                acquired = datetime.fromisoformat(str(existing[0]).replace(" ", "T"))
                if acquired.tzinfo is None:
                    acquired = acquired.replace(tzinfo=timezone.utc)
                if _now() - acquired <= timedelta(seconds=LOCK_TTL_SECONDS):
                    return False
            except (TypeError, ValueError):
                return False
            connection.execute("DELETE FROM role_auto_sync_locks WHERE territory_code=?", (territory,))
        try:
            connection.execute("INSERT INTO role_auto_sync_locks(territory_code,acquired_at) VALUES(?,?)", (territory, _stamp()))
            return True
        except sqlite3.IntegrityError:
            return False


def _release_lock(database_path: Path | str, territory: str) -> None:
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("DELETE FROM role_auto_sync_locks WHERE territory_code=?", (territory,))


def synchronize_selected_municipality(database_path: Path | str, municipality: str, consent: bool, *, fetcher=_official_download, index_fetcher=_official_download) -> AutoSyncResult:
    """Safely synchronize at most one exact official territory after consent.

    The return value contains no address or municipality string.  Failures are
    categorical, short-lived (cooldown), and retain a manual-mode fallback.
    """

    if not consent:
        return AutoSyncResult("consent_required", "Activez la recherche publique ou poursuivez manuellement.")
    if not source_enabled(SOURCE_ID, database_path):
        return AutoSyncResult("source_disabled", "Cette source officielle est désactivée. Vous pouvez poursuivre manuellement.")
    try:
        entry = resolve_official_territory(database_path, municipality, index_fetcher=index_fetcher)
    except Exception:
        return AutoSyncResult("index_unavailable", "L’index officiel est momentanément indisponible. Vous pouvez poursuivre manuellement.")
    if entry is None:
        return AutoSyncResult("not_covered", "Cette municipalité ne peut pas être reliée avec certitude à un territoire officiel. Vous pouvez poursuivre manuellement.")
    territory = entry["territory_code"]
    if _territory_is_disabled(database_path, territory):
        return AutoSyncResult("territory_disabled", "Les données de cette municipalité sont désactivées. Vous pouvez poursuivre manuellement.", territory)
    if _territory_is_available(database_path, territory):
        return AutoSyncResult("available", "Renseignements officiels disponibles.", territory)
    if _cooling_down(database_path, territory):
        return AutoSyncResult("cooldown", "La synchronisation a récemment échoué. Vous pouvez poursuivre manuellement et réessayer plus tard.", territory)
    if not _PROCESS_LOCK.acquire(blocking=False):
        return AutoSyncResult("in_progress", "Synchronisation de cette municipalité en cours. Vous pouvez poursuivre manuellement.", territory)
    if not _acquire_lock(database_path, territory):
        _PROCESS_LOCK.release()
        return AutoSyncResult("in_progress", "Synchronisation de cette municipalité en cours. Vous pouvez poursuivre manuellement.", territory)
    try:
        content = fetcher(_canonical_mamh_url(entry["source_url"]))
        size = len(content)
        checksum = validate_xml(content, MAX_BYTES)
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as temporary:
            temporary.write(content)
            path = temporary.name
        try:
            summary = import_role_xml(path, database_path, territory)
        finally:
            os.unlink(path)
        with closing(sqlite3.connect(database_path)) as connection, connection:
            _record_attempt(connection, territory, "success")
            _record_history(connection, territory, "public_auto_import", "success", "official_xml_validated", checksum=checksum, units=summary["imported_units"])
        return AutoSyncResult("synchronized", "Renseignements officiels disponibles.", territory, summary["imported_units"], size, summary["version"])
    except Exception as error:
        code = str(error) if str(error) in {"official_host_required", "redirect_refused", "official_file_too_large", "official_http_error", "official_network_unavailable"} else type(error).__name__
        with closing(sqlite3.connect(database_path)) as connection, connection:
            _record_attempt(connection, territory, "failed", code)
            _record_history(connection, territory, "public_auto_import", "failed", code)
        return AutoSyncResult("failed", "Les données officielles ne peuvent pas être synchronisées pour le moment. Vous pouvez poursuivre manuellement.", territory)
    finally:
        _release_lock(database_path, territory)
        _PROCESS_LOCK.release()
