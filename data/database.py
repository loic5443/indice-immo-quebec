"""Backward-compatible facade for the SQLite account and analysis services."""

from pathlib import Path
from typing import Any

from domain.models import UserProfile
from migrations.runner import apply_migrations
from services.analysis_service import (
    count_user_analyses,
    delete_user_analysis,
    list_user_analyses,
    save_user_analysis,
    toggle_user_analysis_favorite,
)
from services.auth_service import authenticate_user as _authenticate_user
from services.auth_service import create_user as _create_user
from services.auth_service import get_user as _get_user
from services.auth_service import validate_registration


DATABASE_PATH = Path(__file__).resolve().parent / "immoradar.db"


def initialize_database(database_path: Path | str = DATABASE_PATH) -> list[str]:
    """Apply all pending migrations while preserving the existing SQLite database."""
    return apply_migrations(database_path)


def create_user(
    name: str,
    email: str,
    password: str,
    database_path: Path | str = DATABASE_PATH,
    profile: UserProfile | None = None,
) -> tuple[bool, str]:
    return _create_user(name, email, password, profile or UserProfile(), database_path)


def authenticate_user(email: str, password: str, database_path: Path | str = DATABASE_PATH) -> dict[str, Any] | None:
    return _authenticate_user(email, password, database_path)


def get_user(user_id: int, database_path: Path | str = DATABASE_PATH) -> dict[str, Any] | None:
    return _get_user(user_id, database_path)


def count_analyses(user_id: int, database_path: Path | str = DATABASE_PATH) -> int:
    return count_user_analyses(user_id, database_path)


def save_analysis(
    user_id: int, property_name: str, values: dict[str, float], database_path: Path | str = DATABASE_PATH,
    profile: str = "Investisseur locatif", engine_result=None,
) -> int:
    return save_user_analysis(user_id, property_name, values, database_path, profile, engine_result)


def list_analyses(user_id: int, database_path: Path | str = DATABASE_PATH) -> list[dict[str, Any]]:
    return list_user_analyses(user_id, database_path)


def delete_analysis(user_id: int, analysis_id: int, database_path: Path | str = DATABASE_PATH) -> bool:
    return delete_user_analysis(user_id, analysis_id, database_path)


def toggle_favorite(user_id: int, analysis_id: int, database_path: Path | str = DATABASE_PATH) -> bool:
    return toggle_user_analysis_favorite(user_id, analysis_id, database_path)
