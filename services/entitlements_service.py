"""Single source of truth for plan rights and monthly free-estimation consumption."""
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from repositories.sqlite_repository import SQLiteRepository

def can_use(user, feature): return user.get("role")=="admin" or user.get("plan")=="premium" or feature not in {"alerts","reports","unlimited_estimations","advanced_comparisons"}
def quota_status(user_id,user,database_path,now=None):
 if can_use(user,"unlimited_estimations"): return {"remaining":None,"label":"Illimité"}
 now=now or datetime.now(ZoneInfo("America/Toronto")); period=now.strftime("%Y-%m")
 with closing(SQLiteRepository(database_path)._connect()) as c: used=c.execute("SELECT COUNT(*) FROM monthly_estimation_usage WHERE user_id=? AND period_key=?",(user_id,period)).fetchone()[0]
 return {"remaining":max(0,1-used),"label":f"{max(0,1-used)} estimation complète restante ce mois-ci","period":period}
def consume_estimation(user_id,user,database_path,key):
 status=quota_status(user_id,user,database_path)
 period=status.get("period",datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m"))
 with closing(SQLiteRepository(database_path)._connect()) as c,c:
  if c.execute("SELECT 1 FROM monthly_estimation_usage WHERE user_id=? AND period_key=? AND idempotency_key=?",(user_id,period,key)).fetchone(): return True
  if status["remaining"]==0:return False
  try:c.execute("INSERT INTO monthly_estimation_usage(user_id,period_key,idempotency_key) VALUES(?,?,?)",(user_id,period,key))
  except Exception:return True
 return True
