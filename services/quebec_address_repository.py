"""Local, public-only RQA address coverage for consented suggestions.

The official Référentiel québécois des adresses (RQA) is a monthly MRNF
dataset.  It is used only as a local fallback for address entry: it never
contributes to municipal assessments, ImmoValue, ImmoScore, telemetry or
saved user dossiers.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
import tempfile
import unicodedata
import urllib.error
import urllib.request
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

from domain.address import normalize_canadian_postal_code


SOURCE_ID = "quebec_address_repository"
SOURCE_LABEL = "MRNF — Référentiel québécois des adresses"
RQA_ARCHIVE_URL = "https://diffusion.mern.gouv.qc.ca/diffusion/RGQ/Vectoriel/Theme/Local/RQA/CSV/RQA_CSV.zip"
RQA_DATASET_URL = "https://www.donneesquebec.ca/recherche/dataset/referentiel-quebecois-des-adresses"
OFFICIAL_HOST = "diffusion.mern.gouv.qc.ca"
MAX_ARCHIVE_BYTES = 900_000_000
MAX_UNCOMPRESSED_BYTES = 6_000_000_000
MAX_SUGGESTIONS = 8
BATCH_SIZE = 5_000

REQUIRED_COLUMNS = frozenset({
    "identifiant_unique_adresse", "numero_municipal", "code_postal",
    "odonyme_recompose_normal", "adresse_formatee", "nom_municipalite",
    "code_municipalite", "date_fin", "longitude", "latitude",
})


@dataclass(frozen=True)
class RqaImportResult:
    status: str
    imported_rows: int = 0
    checksum: str = ""
    size_bytes: int = 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: object, maximum: int = 240) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if text and len(text) <= maximum else ""


def _key(value: object) -> str:
    """Normalize an address for a bounded SQLite prefix search only."""

    text = unicodedata.normalize("NFD", _clean(value, 600).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"['’`]+", " ", text)
    text = re.sub(r"\b(rue|avenue|av\.?|boulevard|boul\.?|chemin|route|rang|place|montee|montée)\b", " ", text)
    ignored = {"de", "du", "des", "la", "le", "les", "d", "l", "au", "aux"}
    return " ".join(
        compact for part in text.split()
        if (compact := "".join(char for char in part if char.isalnum())) and compact not in ignored
    )


def _coordinate(value: object, minimum: float, maximum: float) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if minimum <= number <= maximum else None


def _row_values(row: dict[str, str], import_id: int) -> tuple | None:
    """Whitelist only public RQA fields needed for address selection."""

    identifier = _clean(row.get("identifiant_unique_adresse"), 80)
    civic = _clean("".join((
        _clean(row.get("numero_municipal"), 24),
        _clean(row.get("numero_municipal_suffixe"), 12),
    )), 36)
    unit = _clean(row.get("numero_unite"), 32)
    street = _clean(row.get("odonyme_recompose_normal"))
    # The concise municipal label is the one that matches the MAMH role index
    # deterministically.  The longer administrative label is only a fallback.
    city = _clean(row.get("nom_municipalite")) or _clean(row.get("nom_municipalite_complet"))
    formatted = _clean(row.get("adresse_formatee"), 320)
    if not formatted:
        formatted = ", ".join(part for part in (" ".join(part for part in (civic, street) if part), city) if part)
    if not identifier or not formatted or not street or not city:
        return None
    postal = normalize_canadian_postal_code(_clean(row.get("code_postal"), 12)) or ""
    address_key = _key(" ".join(part for part in (civic, street, city, postal) if part))
    street_key = _key(street)
    if not address_key or not street_key:
        return None
    return (
        import_id, identifier, formatted, civic or None, unit or None, street, city,
        _clean(row.get("code_municipalite"), 24) or None, postal or None,
        address_key, street_key,
        _coordinate(row.get("latitude"), 44.0, 63.0),
        _coordinate(row.get("longitude"), -80.0, -57.0),
        0 if _clean(row.get("date_fin"), 32) else 1,
    )


def _archive_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _active_checksum(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT imports.checksum FROM rqa_active_import active "
        "JOIN rqa_imports imports ON imports.id=active.import_id WHERE active.singleton=1"
    ).fetchone()
    return str(row[0]) if row else None


def _archive_csv(archive_path: Path):
    archive = ZipFile(archive_path)
    candidates = [item for item in archive.infolist() if not item.is_dir() and item.filename.lower().endswith(".csv")]
    if len(candidates) != 1 or candidates[0].file_size > MAX_UNCOMPRESSED_BYTES:
        archive.close()
        raise ValueError("rqa_archive_invalid")
    return archive, candidates[0]


def import_rqa_archive(archive_path: Path | str, database_path: Path | str, *, source_url: str = RQA_ARCHIVE_URL) -> RqaImportResult:
    """Stage an RQA snapshot then switch it atomically after full validation.

    The prior snapshot stays searchable until the complete new archive is
    parsed.  A failed download or schema leaves the previous provincial index
    unchanged.
    """

    archive_path = Path(archive_path)
    if not archive_path.is_file() or archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("rqa_archive_invalid")
    checksum = _archive_checksum(archive_path)
    with closing(sqlite3.connect(database_path)) as connection:
        if _active_checksum(connection) == checksum:
            return RqaImportResult("unchanged", checksum=checksum, size_bytes=archive_path.stat().st_size)

    try:
        archive, member = _archive_csv(archive_path)
    except (BadZipFile, OSError) as error:
        raise ValueError("rqa_archive_invalid") from error
    try:
        with archive.open(member) as raw:
            import io
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
                raise ValueError("rqa_schema_invalid")
            with closing(sqlite3.connect(database_path)) as connection, connection:
                cursor = connection.execute(
                    "INSERT INTO rqa_imports(status,checksum,source_url) VALUES('running',?,?)",
                    (checksum, source_url),
                )
                import_id = int(cursor.lastrowid)
            inserted = 0
            batch: list[tuple] = []
            try:
                with closing(sqlite3.connect(database_path)) as connection:
                    # The active snapshot remains untouched while rows are
                    # staged.  Deferring these two indexes until staging is
                    # complete makes the provincial refresh practical without
                    # ever making partial results visible.
                    connection.execute("DROP INDEX IF EXISTS idx_rqa_address_prefix")
                    connection.execute("DROP INDEX IF EXISTS idx_rqa_street_prefix")
                    connection.execute("BEGIN")
                    for row in reader:
                        values = _row_values(row, import_id)
                        if values is None:
                            continue
                        batch.append(values)
                        if len(batch) >= BATCH_SIZE:
                            connection.executemany(
                                "INSERT OR IGNORE INTO rqa_addresses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch,
                            )
                            inserted += len(batch)
                            batch.clear()
                    if batch:
                        connection.executemany("INSERT OR IGNORE INTO rqa_addresses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
                        inserted += len(batch)
                    connection.commit()
                    connection.execute("CREATE INDEX IF NOT EXISTS idx_rqa_address_prefix ON rqa_addresses(import_id, active, address_search_key)")
                    connection.execute("CREATE INDEX IF NOT EXISTS idx_rqa_street_prefix ON rqa_addresses(import_id, active, street_search_key)")
                if not inserted:
                    raise ValueError("rqa_no_valid_addresses")
            except Exception:
                with closing(sqlite3.connect(database_path)) as connection, connection:
                    connection.execute("DELETE FROM rqa_addresses WHERE import_id=?", (import_id,))
                    connection.execute("UPDATE rqa_imports SET status='failed',completed_at=? WHERE id=?", (_now(), import_id))
                    connection.execute("CREATE INDEX IF NOT EXISTS idx_rqa_address_prefix ON rqa_addresses(import_id, active, address_search_key)")
                    connection.execute("CREATE INDEX IF NOT EXISTS idx_rqa_street_prefix ON rqa_addresses(import_id, active, street_search_key)")
                raise
    finally:
        archive.close()

    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("UPDATE rqa_imports SET status='ready',imported_rows=?,completed_at=? WHERE id=?", (inserted, _now(), import_id))
        connection.execute(
            "INSERT INTO rqa_active_import(singleton,import_id,updated_at) VALUES(1,?,?) "
            "ON CONFLICT(singleton) DO UPDATE SET import_id=excluded.import_id,updated_at=excluded.updated_at",
            (import_id, _now()),
        )
        connection.execute("DELETE FROM rqa_addresses WHERE import_id<>?", (import_id,))
        connection.execute("DELETE FROM rqa_imports WHERE id<>?", (import_id,))
    return RqaImportResult("ready", inserted, checksum, archive_path.stat().st_size)


def _download_archive(url: str, destination: Path) -> int:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
        raise ValueError("official_host_required")
    request = urllib.request.Request(url, headers={"User-Agent": "ImmoRadar/1.0 official-data"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > MAX_ARCHIVE_BYTES:
                raise ValueError("rqa_archive_too_large")
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError("rqa_archive_too_large")
                output.write(chunk)
            return total
    except (urllib.error.HTTPError, urllib.error.URLError) as error:
        raise ValueError("rqa_download_unavailable") from error


def synchronize_rqa_snapshot(database_path: Path | str, *, url: str = RQA_ARCHIVE_URL) -> RqaImportResult:
    """Download one official RQA archive temporarily and import it safely."""

    temporary = tempfile.NamedTemporaryFile(prefix="immoradar-rqa-", suffix=".zip", delete=False)
    archive_path = Path(temporary.name)
    temporary.close()
    try:
        _download_archive(url, archive_path)
        return import_rqa_archive(archive_path, database_path, source_url=url)
    finally:
        archive_path.unlink(missing_ok=True)


def rqa_status(database_path: Path | str) -> dict[str, int | str | None]:
    """Return aggregate local coverage only; never return an address."""

    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT imports.imported_rows,imports.completed_at FROM rqa_active_import active "
            "JOIN rqa_imports imports ON imports.id=active.import_id WHERE active.singleton=1"
        ).fetchone()
    return {"status": "ready" if row else "not_loaded", "addresses": int(row[0]) if row else 0, "updated_at": row[1] if row else None}


def present_rqa_text(value: object) -> str:
    """Return a readable label without changing the stored official value."""

    text = _clean(value, 320)
    if not text or text != text.upper():
        return text
    # RQA's display labels are often uppercase.  This is presentation only;
    # apostrophes and Québec hyphenation remain intact in the stored record.
    return text.title().replace(" D'", " d'").replace(" L'", " l'")


def suggest_rqa_addresses(database_path: Path | str, query: str, limit: int = MAX_SUGGESTIONS) -> list[dict[str, object]]:
    """Search the active provincial cache in SQLite, never in Python memory."""

    query_key = _key(query)
    if len("".join(query_key.split())) < 3:
        return []
    maximum = max(1, min(int(limit), MAX_SUGGESTIONS))
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        columns = "address_text,civic_number,unit,street_name,municipality,postal_code,latitude,longitude"
        base = (
            " FROM rqa_addresses addresses JOIN rqa_active_import active ON active.import_id=addresses.import_id "
            "WHERE active.singleton=1 AND addresses.active=1 AND "
        )
        # Two bounded indexed reads are intentionally preferable to one OR +
        # ORDER BY query.  A common street name can match tens of thousands
        # of rows; sorting them merely to display eight would stall typing.
        address_rows = connection.execute(
            f"SELECT {columns}{base}addresses.address_search_key GLOB ? LIMIT ?",
            (f"{query_key}*", maximum),
        ).fetchall()
        remaining = maximum - len(address_rows)
        street_rows = connection.execute(
            f"SELECT {columns}{base}addresses.street_search_key GLOB ? LIMIT ?",
            (f"{query_key}*", max(0, remaining)),
        ).fetchall() if remaining else []
    results: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in [*address_rows, *street_rows]:
        item = dict(row)
        identity = (
            str(item.get("address_text") or ""), str(item.get("municipality") or ""),
            str(item.get("postal_code") or ""), str(item.get("unit") or ""),
        )
        if identity not in seen:
            results.append(item)
            seen.add(identity)
    return results[:maximum]
