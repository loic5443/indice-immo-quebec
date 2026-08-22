"""Password-safe local account service."""

import hashlib
import hmac
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domain.models import UserProfile
from repositories.sqlite_repository import SQLiteRepository


PASSWORD_ITERATIONS = 260_000
MAX_NAME_LENGTH = 80
MAX_EMAIL_LENGTH = 254


def validate_login_submission(email: str, password: str) -> list[str]:
    """Validate only missing credentials; credential mismatches stay generic."""
    errors: list[str] = []
    if not email.strip():
        errors.append("Le courriel est requis.")
    if not password:
        errors.append("Le mot de passe est requis.")
    return errors


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    actual_salt = salt or os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, PASSWORD_ITERATIONS)
    return derived_key.hex(), actual_salt.hex()


def validate_registration(name: str, email: str, password: str, confirmation: str, profile: UserProfile | None = None) -> list[str]:
    """Validate account and profile inputs before storing anything."""
    errors: list[str] = []
    normalized_name = name.strip()
    normalized_email = email.strip()
    if len(normalized_name) < 2:
        errors.append("Veuillez saisir un nom d'au moins 2 caractères.")
    elif len(normalized_name) > MAX_NAME_LENGTH or any(ord(character) < 32 for character in normalized_name):
        errors.append("Le nom doit contenir au plus 80 caractères lisibles.")
    if (
        len(normalized_email) > MAX_EMAIL_LENGTH
        or normalized_email.count("@") != 1
        or normalized_email.startswith("@")
        or normalized_email.endswith("@")
        or any(character.isspace() for character in normalized_email)
    ):
        errors.append("Veuillez saisir une adresse courriel valide.")
    if len(password) < 12:
        errors.append("Le mot de passe doit contenir au moins 12 caractères.")
    if password != confirmation:
        errors.append("La confirmation du mot de passe ne correspond pas.")
    if profile and not all((profile.user_type, profile.investment_horizon, profile.risk_tolerance)):
        errors.append("Veuillez compléter votre profil investisseur.")
    return errors


def create_user(name: str, email: str, password: str, profile: UserProfile, database_path: Path | str) -> tuple[bool, str]:
    password_hash, password_salt = _hash_password(password)
    created = SQLiteRepository(database_path).create_user({
        "name": name.strip(), "email": email.strip().lower(), "password_hash": password_hash,
        "password_salt": password_salt, "created_at": _now(), "user_type": profile.user_type,
        "investment_horizon": profile.investment_horizon, "risk_tolerance": profile.risk_tolerance,
    })
    if not created:
        return False, "Un compte existe déjà pour cette adresse courriel."
    return True, "Compte créé. Vous pouvez maintenant vous connecter."


def authenticate_user(email: str, password: str, database_path: Path | str) -> dict[str, Any] | None:
    user = SQLiteRepository(database_path).get_user_by_email(email.strip().lower())
    if user is None:
        return None
    attempted_hash, _ = _hash_password(password, bytes.fromhex(user["password_salt"]))
    if not hmac.compare_digest(attempted_hash, user["password_hash"]):
        return None
    return _public_user(user)


def get_user(user_id: int, database_path: Path | str) -> dict[str, Any] | None:
    user = SQLiteRepository(database_path).get_user_by_id(user_id)
    return _public_user(user) if user else None


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {key: user[key] for key in ("id", "name", "email", "plan", "user_type", "investment_horizon", "risk_tolerance", "role", "onboarding_completed", "onboarding_step", "user_objective", "limitations_accepted", "marketing_consent", "analytics_consent", "alert_email_consent")}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
