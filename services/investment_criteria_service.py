"""Persist owner-specific Premium criteria and screen only owned snapshots."""
import json
import time
from contextlib import closing

from domain.investment_criteria import screen_snapshot, validate_criteria
from repositories.sqlite_repository import SQLiteRepository
from services.auth_service import get_user
from services.entitlements_service import can_use


class CriteriaAccessError(PermissionError):
    pass


def _authorized(user_id, database_path):
    user = get_user(user_id, database_path)
    if not user or not can_use(user, "investment_criteria"):
        raise CriteriaAccessError("Les critères personnalisés nécessitent un accès Premium.")


def get_criteria(user_id, database_path):
    _authorized(user_id, database_path)
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        row = connection.execute("SELECT criteria_json FROM investment_criteria WHERE user_id=?", (user_id,)).fetchone()
    return validate_criteria(json.loads(row[0])) if row else {}


def save_criteria(user_id, criteria, database_path):
    _authorized(user_id, database_path)
    criteria = validate_criteria(criteria)
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("INSERT INTO investment_criteria VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET criteria_json=excluded.criteria_json,updated_at=excluded.updated_at",
                           (user_id, json.dumps(criteria), int(time.time())))


def screen_owned_analysis(user_id, analysis_id, database_path):
    criteria = get_criteria(user_id, database_path)
    analysis = SQLiteRepository(database_path).get_owned_analysis(user_id, analysis_id)
    if analysis is None:
        raise CriteriaAccessError("Ce dossier n’est pas disponible dans votre espace.")
    return screen_snapshot(analysis, criteria)


def price_ceiling_for_snapshot(analysis, criteria):
    from dataclasses import fields
    from calculations.real_estate import PropertyInputs
    from domain.investment_criteria import financing_price_ceiling
    try:
        payload = json.loads(analysis.get("financial_inputs_json") or "{}")
        names = {field.name for field in fields(PropertyInputs)}
        inputs = PropertyInputs(**{key: value for key, value in payload.items() if key in names})
        return financing_price_ceiling(inputs, criteria)
    except (TypeError, ValueError, AttributeError):
        return {"status": "unavailable", "price": None, "reason": "Complétez les hypothèses financières et recalculer le dossier pour simuler un plafond."}
