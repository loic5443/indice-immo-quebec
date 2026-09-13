"""Resumable, one-territory-at-a-time coverage sync for official MAMH roles."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from services.diagnostics_service import source_enabled
from services.quebec_role_auto_sync import (
    SOURCE_ID, _official_download, _synchronize_entry, _territory_is_available,
    _territory_is_disabled, probe_role_xml_version,
)


DEFAULT_BATCH_TERRITORIES = 10
DEFAULT_BATCH_BYTES = 250_000_000


@dataclass(frozen=True)
class CoverageSyncResult:
    run_id: str
    status: str
    scanned: int
    synchronized: int
    skipped: int
    failed: int
    downloaded_bytes: int
    remaining: int


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def coverage_status(database_path: Path | str) -> dict[str, int]:
    """Return aggregate coverage only; no entered address leaves SQLite."""
    with closing(sqlite3.connect(database_path)) as connection:
        indexed = connection.execute("SELECT COUNT(*) FROM role_index_entries").fetchone()[0]
        imported = connection.execute("SELECT COUNT(*) FROM role_territory_imports").fetchone()[0]
        units = connection.execute("SELECT COUNT(*) FROM role_assessment_units").fetchone()[0]
    return {"indexed": int(indexed), "imported": int(imported), "remaining": max(0, int(indexed) - int(imported)), "units": int(units)}


def _eligible_entries(database_path: Path | str) -> list[dict[str, str]]:
    """Return only active, stale/missing territories from the official index."""
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT territory_code, municipality, source_url, source_updated_at FROM role_index_entries ORDER BY territory_code"
        ).fetchall()
    eligible: list[dict[str, str]] = []
    for row in rows:
        entry = dict(row)
        code = entry["territory_code"]
        if not _territory_is_disabled(database_path, code) and not _territory_is_available(database_path, code):
            eligible.append(entry)
    return eligible


def _start_run(database_path: Path | str, territory_limit: int | None, byte_budget: int) -> str:
    run_id = uuid.uuid4().hex
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            "INSERT INTO role_coverage_runs(run_id,started_at,status,requested_limit,byte_budget) VALUES(?,?,?,?,?)",
            (run_id, _stamp(), "running", territory_limit, byte_budget),
        )
    return run_id


def _finish_run(database_path: Path | str, result: CoverageSyncResult) -> None:
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            """UPDATE role_coverage_runs SET completed_at=?,status=?,scanned_territories=?,synchronized_territories=?,
            skipped_territories=?,failed_territories=?,downloaded_bytes=? WHERE run_id=?""",
            (_stamp(), result.status, result.scanned, result.synchronized, result.skipped, result.failed, result.downloaded_bytes, result.run_id),
        )


def synchronize_role_coverage(
    database_path: Path | str, *, territory_limit: int | None = DEFAULT_BATCH_TERRITORIES,
    byte_budget: int = DEFAULT_BATCH_BYTES, fetcher=_official_download, version_fetcher=probe_role_xml_version,
) -> CoverageSyncResult:
    """Sync a bounded batch. ``None`` is an explicit all-territories request."""
    if territory_limit is not None and territory_limit < 1:
        raise ValueError("territory_limit_required")
    if byte_budget < 1:
        raise ValueError("byte_budget_required")
    if not source_enabled(SOURCE_ID, database_path):
        raise ValueError("official_source_disabled")

    run_id = _start_run(database_path, territory_limit, byte_budget)
    scanned = synchronized = skipped = failed = downloaded = 0
    try:
        entries = _eligible_entries(database_path)
        candidates = entries if territory_limit is None else entries[:territory_limit]
        for entry in candidates:
            if downloaded >= byte_budget:
                break
            scanned += 1
            result = _synchronize_entry(database_path, entry, True, fetcher=fetcher, version_fetcher=version_fetcher)
            if result.status == "synchronized":
                synchronized += 1
                downloaded += result.size_bytes
            elif result.status == "available":
                skipped += 1
            else:
                failed += 1
        remaining = len(_eligible_entries(database_path))
        status = "completed" if remaining == 0 else "stopped"
        output = CoverageSyncResult(run_id, status, scanned, synchronized, skipped, failed, downloaded, remaining)
        _finish_run(database_path, output)
        return output
    except Exception:
        output = CoverageSyncResult(run_id, "failed", scanned, synchronized, skipped, failed + 1, downloaded, len(_eligible_entries(database_path)))
        _finish_run(database_path, output)
        raise
