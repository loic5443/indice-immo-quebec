"""Owner-scoped local follow selections for factual in-app alerts."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from repositories.sqlite_repository import SQLiteRepository
from services.snapshot_history_service import canonical_dossier_key


class DossierTrackingAccessError(PermissionError):
    """Raised without revealing a dossier owned by another account."""


def dossier_fingerprint(user_id: int, property_name: object) -> str:
    """Return a local irreversible key; the tracked table never stores the name."""

    key = canonical_dossier_key(property_name)
    if not key:
        raise ValueError("Un dossier nommé est requis pour activer le suivi.")
    return sha256(f"{int(user_id)}:{key}".encode("utf-8")).hexdigest()


def tracked_dossier_fingerprints(user_id: int, database_path: Path | str) -> set[str]:
    return SQLiteRepository(database_path).tracked_dossier_fingerprints(user_id)


def set_dossier_tracking(user_id: int, analysis_id: int, enabled: bool, database_path: Path | str) -> None:
    """Change follow status only after resolving the analysis in the owner's scope."""

    repository = SQLiteRepository(database_path)
    analysis = repository.get_owned_analysis(user_id, analysis_id)
    if analysis is None:
        raise DossierTrackingAccessError("Ce dossier n’est pas disponible dans votre espace.")
    repository.set_dossier_tracking(user_id, dossier_fingerprint(user_id, analysis.get("property_name")), enabled)


def filter_tracked_analyses(user_id: int, analyses: list[dict[str, Any]], database_path: Path | str) -> list[dict[str, Any]]:
    """Filter an already owner-scoped snapshot list without exposing another account."""

    fingerprints = tracked_dossier_fingerprints(user_id, database_path)
    return [
        analysis for analysis in analyses
        if dossier_fingerprint(user_id, analysis.get("property_name")) in fingerprints
    ]
