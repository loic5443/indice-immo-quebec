"""Safe diagnostic storage and source controls; no raw user data enters these records."""
import re
from contextlib import closing
from repositories.sqlite_repository import SQLiteRepository

FORBIDDEN=("password","token","secret","hash","invitation","email","address","price","income","expense","comparable","csv","pdf")
def redact(text):
 text=str(text)[:300]
 if any(word in text.lower() for word in FORBIDDEN): return "[expurgé]"
 return re.sub(r"[A-Za-z]:\\[^\s]+|/[^\s]+", "[chemin expurgé]", text)
def set_source_enabled(actor,source_id,enabled,reason,database_path):
 if not reason.strip(): raise ValueError("Raison requise.")
 with closing(SQLiteRepository(database_path)._connect()) as c,c:
  role=c.execute("SELECT role FROM users WHERE id=?",(actor,)).fetchone()
  if not role or role[0]!="admin": raise PermissionError("Accès refusé")
  c.execute("UPDATE data_sources SET enabled=? WHERE source_id=?",(int(enabled),source_id));c.execute("INSERT INTO source_admin_history(source_id,actor_id,action,reason) VALUES(?,?,?,?)",(source_id,actor,"enabled" if enabled else "disabled",redact(reason)))
def source_enabled(source_id,database_path):
 with closing(SQLiteRepository(database_path)._connect()) as c: row=c.execute("SELECT enabled FROM data_sources WHERE source_id=?",(source_id,)).fetchone()
 return True if row is None else bool(row[0])
def record_error(component,code,message,database_path):
 clean=redact(message)
 if clean=="[expurgé]": return False
 with closing(SQLiteRepository(database_path)._connect()) as c,c:c.execute("INSERT INTO technical_errors(component,error_code,level,message) VALUES(?,?,?,?)",(component,code,"error",clean))
 return True
