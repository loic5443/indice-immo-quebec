"""Central privacy-preserving telemetry: strict allowlist, consent and idempotence."""
from contextlib import closing
from datetime import datetime, timezone
from repositories.sqlite_repository import SQLiteRepository

ALLOWED_EVENTS={"account_created","onboarding_started","onboarding_completed","analysis_started","analysis_completed","immovalue_generated","immovalue_refused","analysis_saved","report_generated","feedback_submitted","account_exported","account_deleted"}
ALLOWED_FIELDS={"event_name","event_version","occurred_at","application_version","engine_version","immovalue_version","page_code","outcome_code","authenticated","plan_code","duration_bucket","error_code"}
SENSITIVE=("password","hash","salt","token","secret","invitation","email","name","address","postal","price","down_payment","income","expense","debt","rent","comparable","comment","note","file","pdf","csv")
def validate_payload(payload):
 if set(payload)-ALLOWED_FIELDS: raise ValueError("Champ de télémétrie non autorisé.")
 text=" ".join(str(v).lower() for v in payload.values())
 if any(word in text for word in SENSITIVE): raise ValueError("Charge sensible rejetée.")
 if payload.get("event_name") not in ALLOWED_EVENTS: raise ValueError("Événement non autorisé.")
def record_event(user_id,payload,database_path,consent=True,idempotency_key=None):
 if isinstance(payload,str): payload={"event_name":payload}
 if not consent: return False
 validate_payload(payload)
 repo=SQLiteRepository(database_path)
 with closing(repo._connect()) as c,c:
  try:
   c.execute("INSERT INTO privacy_events(user_id,event_type,event_version,outcome_code,idempotency_key,created_at) VALUES(?,?,?,?,?,?)",(user_id,payload["event_name"],payload.get("event_version","1"),payload.get("outcome_code","ok"),idempotency_key,datetime.now(timezone.utc).isoformat()))
  except Exception: return False
 return True
def aggregate_events(database_path,min_users=5):
 with closing(SQLiteRepository(database_path)._connect()) as c: rows=c.execute("SELECT event_type,COUNT(*) n,COUNT(DISTINCT user_id) u FROM privacy_events GROUP BY event_type").fetchall()
 return {r[0]:r[1] if r[2]>=min_users else None for r in rows}
