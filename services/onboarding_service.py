"""Persistent, local onboarding workflow independent from Streamlit widgets."""
from datetime import datetime, timezone
from contextlib import closing
from repositories.sqlite_repository import SQLiteRepository
from services.telemetry_service import record_event

STEPS = ("Bienvenue", "Profil", "Objectif", "Horizon", "Risque", "ImmoValue", "ImmoScore", "Confiance", "Limites")

def progress(user_id, database_path, **values):
    repository=SQLiteRepository(database_path)
    fields={key:value for key,value in values.items() if key in {"onboarding_step","user_type","user_objective","investment_horizon","risk_tolerance","limitations_accepted","marketing_consent","analytics_consent"}}
    if not fields: return
    sql=", ".join(f"{key}=?" for key in fields)
    with closing(repository._connect()) as connection, connection:
        connection.execute(f"UPDATE users SET {sql} WHERE id=?", (*fields.values(),user_id))

def complete(user_id, database_path):
    user=SQLiteRepository(database_path).get_user_by_id(user_id)
    if not user or not user.get("user_type") or not user.get("user_objective") or not user.get("limitations_accepted"): return False
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("UPDATE users SET onboarding_completed=1,onboarding_completed_at=?,onboarding_step=9 WHERE id=?",(datetime.now(timezone.utc).isoformat(),user_id))
    record_event(user_id,"onboarding_completed",database_path,bool(user.get("analytics_consent")))
    return True
