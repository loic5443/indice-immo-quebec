"""Controlled, consent-first synchronization of one official Quebec role.

This service never receives or stores an address.  It receives only a
municipality name already returned by an explicitly selected public address,
resolves it exactly in the official MAMH index, and imports one territory.
"""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
import threading
import urllib.error
import urllib.request
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from services.diagnostics_service import source_enabled
from services.quebec_role_importer import SUPPORTED_XML_VERSIONS, import_role_xml
from services.quebec_role_sync import INDEX_URL, municipality_key, parse_index, validate_xml


SOURCE_ID = "mamh_quebec_assessment_rolls"
OFFICIAL_HOSTS = frozenset({"mamh.gouv.qc.ca", "www.mamh.gouv.qc.ca"})
MAX_BYTES = 20_000_000
TIMEOUT_SECONDS = 15
COOLDOWN_SECONDS = 300
LOCK_TTL_SECONDS = 300
INDEX_REFRESH_MAX_AGE = timedelta(days=7)
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

    return municipality_key(value)


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


def probe_role_xml_version(url: str) -> str:
    """Read only an official XML header before downloading a full territory.

    This preflight request is intentionally bounded and never stores a role
    payload.  It prevents a known unsupported format from consuming a full
    municipal download during a user-initiated synchronization.
    """

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise ValueError("official_host_required")
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ImmoRadar/1.0 official-data", "Range": "bytes=0-4095"},
    )
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.geturl() != url:
                raise ValueError("redirect_refused")
            header = response.read(4096)
    except urllib.error.HTTPError as error:
        raise ValueError("official_http_error") from error
    except urllib.error.URLError as error:
        raise ValueError("official_network_unavailable") from error
    match = re.search(br"<VERSION>\s*([^<\s]{1,20})\s*</VERSION>", header)
    if not match:
        raise ValueError("official_xml_header_invalid")
    return match.group(1).decode("ascii", "strict")


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


def _index_entry_for_territory(database_path: Path | str, territory_code: str) -> dict | None:
    """Return exactly one official MAMH index row for a geographic code.

    RQA and the MAMH role index both publish geographic territory codes.  The
    code is accepted only when it is already present as an exact official
    index entry; a city-name similarity never substitutes for this check.
    """

    code = str(territory_code or "").strip()
    if not re.fullmatch(r"\d{5}", code):
        return None
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT territory_code,municipality,source_url,source_updated_at FROM role_index_entries WHERE territory_code=?",
            (code,),
        ).fetchone()
    return dict(row) if row else None


def _index_needs_refresh(database_path: Path | str) -> bool:
    """Refresh the small official catalogue occasionally, never on rendering.

    Role XML files are still requested only for the one municipality selected
    by the person.  Refreshing this index lets new official territories become
    eligible without an administrator having to rebuild the local catalogue.
    """

    with closing(sqlite3.connect(database_path)) as connection:
        count, latest = connection.execute(
            "SELECT COUNT(*), MAX(index_synced_at) FROM role_index_entries"
        ).fetchone()
    if not count or not latest:
        return True
    try:
        refreshed = datetime.fromisoformat(str(latest).replace("Z", "+00:00"))
        if refreshed.tzinfo is None:
            refreshed = refreshed.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return _now() - refreshed >= INDEX_REFRESH_MAX_AGE


def _refresh_index_if_needed(database_path: Path | str, index_fetcher) -> None:
    if not _index_needs_refresh(database_path):
        return
    rows = parse_index(index_fetcher(INDEX_URL))
    if not rows:
        raise ValueError("official_index_empty")
    now = _stamp()
    with closing(sqlite3.connect(database_path)) as connection, connection:
        # Replace the catalogue atomically so a removed or changed official
        # entry cannot survive as a stale eligible territory.
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TEMP TABLE incoming_role_index AS SELECT * FROM role_index_entries WHERE 0")
        connection.executemany(
            "INSERT INTO incoming_role_index(territory_code,municipality,source_url,source_updated_at,index_synced_at) VALUES(?,?,?,?,?)",
            [(row["territory_code"], row["municipality"], row["url"], row["updated_at"], now) for row in rows],
        )
        connection.execute("DELETE FROM role_index_entries")
        connection.execute("INSERT INTO role_index_entries SELECT * FROM incoming_role_index")
        _record_history(connection, "*", "public_index_refresh", "success", "official_index")


def resolve_official_territory(database_path: Path | str, municipality: str, *, index_fetcher=_official_download) -> dict | None:
    """Resolve one municipality only through an exact official-index entry."""

    entry = _index_entry(database_path, municipality)
    if entry is None or _index_needs_refresh(database_path):
        _refresh_index_if_needed(database_path, index_fetcher)
        entry = _index_entry(database_path, municipality)
    return entry


def resolve_official_territory_code(
    database_path: Path | str, territory_code: str, *, index_fetcher=_official_download,
) -> dict | None:
    """Resolve an RQA geographic code only against the official MAMH index."""

    entry = _index_entry_for_territory(database_path, territory_code)
    if entry is None or _index_needs_refresh(database_path):
        _refresh_index_if_needed(database_path, index_fetcher)
        entry = _index_entry_for_territory(database_path, territory_code)
    return entry


def _territory_is_available(database_path: Path | str, territory: str) -> bool:
    """Return whether a local role is active and no older than MAMH's index.

    A cached role remains useful after a failed refresh, but it must not stop
    a later selected-address action from refreshing when the official index
    advertises a newer territorial XML.  Missing or malformed index dates are
    deliberately treated as "unknown, keep cache" rather than causing a
    download loop.
    """

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            """SELECT imported.territory_code,imported.synced_at,role_index.source_updated_at
            FROM role_territory_imports imported
            JOIN role_index_entries role_index ON role_index.territory_code=imported.territory_code
            LEFT JOIN role_territory_settings settings ON settings.territory_code=imported.territory_code
            WHERE imported.territory_code=? AND COALESCE(settings.enabled,1)=1""",
            (territory,),
        ).fetchone()
    if not row:
        return False
    try:
        imported_at = datetime.fromisoformat(str(row[1]).replace("Z", "+00:00").replace(" ", "T"))
        updated_at = datetime.fromisoformat(str(row[2]).replace("Z", "+00:00").replace(" ", "T"))
        if imported_at.tzinfo is None:
            imported_at = imported_at.replace(tzinfo=timezone.utc)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return True
    return imported_at >= updated_at


def _territory_is_disabled(database_path: Path | str, territory: str) -> bool:
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute("SELECT enabled FROM role_territory_settings WHERE territory_code=?", (territory,)).fetchone()
    return bool(row and not row[0])


def municipal_coverage_status(database_path: Path | str, municipality: str) -> dict[str, str]:
    """Describe one municipality's local role coverage without any network call.

    The result deliberately contains only a categorical state and an internal
    territory code.  It never includes the entered address or municipality
    text, and it never refreshes the official index as part of a form render.
    """

    entry = _index_entry(database_path, municipality)
    return _coverage_status_for_entry(database_path, entry)


def municipal_coverage_status_for_territory(database_path: Path | str, territory_code: str) -> dict[str, str]:
    """Describe one exact selected RQA territory without a network request."""

    entry = _index_entry_for_territory(database_path, territory_code)
    return _coverage_status_for_entry(database_path, entry)


def _coverage_status_for_entry(database_path: Path | str, entry: dict | None) -> dict[str, str]:
    """Return a categorical local coverage state for one official index entry."""

    if entry is None:
        return {"status": "manual", "territory_code": ""}
    territory = entry["territory_code"]
    if not source_enabled(SOURCE_ID, database_path):
        return {"status": "source_disabled", "territory_code": territory}
    if _territory_is_disabled(database_path, territory):
        return {"status": "territory_disabled", "territory_code": territory}
    if _territory_is_available(database_path, territory):
        return {"status": "available", "territory_code": territory}
    if _cooling_down(database_path, territory):
        return {"status": "retry_later", "territory_code": territory}
    return {"status": "sync_available", "territory_code": territory}


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


def _synchronize_entry(
    database_path: Path | str,
    entry: dict | None,
    consent: bool,
    *,
    fetcher=_official_download,
    version_fetcher=probe_role_xml_version,
    maximum_bytes: int = MAX_BYTES,
) -> AutoSyncResult:
    """Safely synchronize at most one already-validated official territory.

    The return value contains no address or municipality string.  Failures are
    categorical, short-lived (cooldown), and retain a manual-mode fallback.
    """

    if not consent:
        return AutoSyncResult("consent_required", "Activez la recherche publique ou poursuivez manuellement.")
    if not source_enabled(SOURCE_ID, database_path):
        return AutoSyncResult("source_disabled", "Cette source officielle est désactivée. Vous pouvez poursuivre manuellement.")
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
        source_url = _canonical_mamh_url(entry["source_url"])
        version = version_fetcher(source_url)
        if version not in SUPPORTED_XML_VERSIONS:
            raise ValueError("Version ou année XML invalide.")
        content = fetcher(source_url)
        size = len(content)
        # The public consent flow keeps ``MAX_BYTES``. A separate, explicit
        # coverage job can pass its independently tested maintenance ceiling.
        checksum = validate_xml(content, maximum_bytes)
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
        unsupported_format = str(error) == "Version ou année XML invalide."
        code = (
            "unsupported_xml_format"
            if unsupported_format
            else str(error)
            if str(error) in {"official_host_required", "redirect_refused", "official_file_too_large", "official_http_error", "official_network_unavailable"}
            else type(error).__name__
        )
        with closing(sqlite3.connect(database_path)) as connection, connection:
            _record_attempt(connection, territory, "failed", code)
            _record_history(connection, territory, "public_auto_import", "failed", code)
        if unsupported_format:
            return AutoSyncResult("unsupported_format", "Le rôle municipal officiel utilise un format qui n’est pas encore pris en charge. Vous pouvez poursuivre manuellement.", territory)
        return AutoSyncResult("failed", "Les données officielles ne peuvent pas être synchronisées pour le moment. Vous pouvez poursuivre manuellement.", territory)
    finally:
        _release_lock(database_path, territory)
        _PROCESS_LOCK.release()


def synchronize_selected_municipality(database_path: Path | str, municipality: str, consent: bool, *, fetcher=_official_download, index_fetcher=_official_download, version_fetcher=probe_role_xml_version) -> AutoSyncResult:
    """Synchronize one municipality after an exact official-index lookup."""

    if not consent:
        return AutoSyncResult("consent_required", "Activez la recherche publique ou poursuivez manuellement.")
    try:
        entry = resolve_official_territory(database_path, municipality, index_fetcher=index_fetcher)
    except Exception:
        return AutoSyncResult("index_unavailable", "L’index officiel est momentanément indisponible. Vous pouvez poursuivre manuellement.")
    return _synchronize_entry(database_path, entry, consent, fetcher=fetcher, version_fetcher=version_fetcher)


def synchronize_selected_territory(database_path: Path | str, territory_code: str, consent: bool, *, fetcher=_official_download, index_fetcher=_official_download, version_fetcher=probe_role_xml_version) -> AutoSyncResult:
    """Synchronize the one RQA-selected territory when its code is official.

    This route is deliberately code-only: a selected RQA row cannot trigger a
    municipal import through a fuzzy city-name match.
    """

    if not consent:
        return AutoSyncResult("consent_required", "Activez la recherche publique ou poursuivez manuellement.")
    try:
        entry = resolve_official_territory_code(database_path, territory_code, index_fetcher=index_fetcher)
    except Exception:
        return AutoSyncResult("index_unavailable", "L’index officiel est momentanément indisponible. Vous pouvez poursuivre manuellement.")
    return _synchronize_entry(database_path, entry, consent, fetcher=fetcher, version_fetcher=version_fetcher)
