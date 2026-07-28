"""Saved-analysis service with ImmoEngine traceability metadata."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from providers.data_provenance import IMMOENGINE_METADATA
from repositories.sqlite_repository import SQLiteRepository


def save_user_analysis(user_id: int, property_name: str, values: dict[str, float], database_path: Path | str) -> int:
    """Persist user assumptions and calculated outputs; no value estimate is produced."""
    payload: dict[str, Any] = {
        **values,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "engine_version": IMMOENGINE_METADATA.version,
        "data_provenance": IMMOENGINE_METADATA.data_provenance,
    }
    return SQLiteRepository(database_path).save_analysis(user_id, property_name.strip(), payload)


def list_user_analyses(user_id: int, database_path: Path | str) -> list[dict[str, Any]]:
    return SQLiteRepository(database_path).list_analyses(user_id)


def count_user_analyses(user_id: int, database_path: Path | str) -> int:
    return SQLiteRepository(database_path).count_analyses(user_id)


def delete_user_analysis(user_id: int, analysis_id: int, database_path: Path | str) -> bool:
    return SQLiteRepository(database_path).delete_analysis(user_id, analysis_id)


def toggle_user_analysis_favorite(user_id: int, analysis_id: int, database_path: Path | str) -> bool:
    return SQLiteRepository(database_path).toggle_favorite(user_id, analysis_id)
