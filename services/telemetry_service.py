"""Minimal event logging: no address, financial values, comparables, PDF or credentials."""
from repositories.sqlite_repository import SQLiteRepository
from contextlib import closing

ALLOWED_EVENTS={"account_created","onboarding_completed","analysis_started","analysis_completed","immovalue_produced","immovalue_refused","report_generated","analysis_saved","feedback_sent"}
def record_event(user_id, event_type, database_path, enabled=True):
    if not enabled or event_type not in ALLOWED_EVENTS: return
    repository=SQLiteRepository(database_path)
    with closing(repository._connect()) as connection, connection:
        connection.execute("INSERT INTO privacy_events(user_id,event_type) VALUES (?,?)",(user_id,event_type))
