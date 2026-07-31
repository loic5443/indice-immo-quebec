"""Private beta invitations: opaque codes are shown once and stored only as hashes."""
import hashlib,secrets
import csv
from io import StringIO
from contextlib import closing
from datetime import datetime,timezone
from repositories.sqlite_repository import SQLiteRepository

def _hash(code): return hashlib.sha256(code.encode()).hexdigest()
def create_invitation(actor_id,database_path,label="",max_uses=1,expires_at=None):
 code=secrets.token_urlsafe(18); repo=SQLiteRepository(database_path)
 with closing(repo._connect()) as c,c:
  c.execute("INSERT INTO beta_invitations(code,code_hash,label,max_uses,creator_id,expires_at) VALUES(?,?,?,?,?,?)",(secrets.token_hex(16),_hash(code),label,max_uses,actor_id,expires_at));c.execute("INSERT INTO admin_audit_log(actor_id,action,metadata) VALUES(?,?,?)",(actor_id,"invitation_created",'{}'))
 return code
def invitation_status(row):
 if not row or not row["active"]: return "revoked"
 if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc).isoformat(): return "expired"
 return "exhausted" if row["uses_count"]>=row["max_uses"] else "active"
def validate_invitation(code,database_path):
 with closing(SQLiteRepository(database_path)._connect()) as c:
  row=c.execute("SELECT * FROM beta_invitations WHERE code_hash=?",(_hash(code),)).fetchone()
 return invitation_status(row)
def revoke_invitation(actor_id, invitation_id,database_path):
 with closing(SQLiteRepository(database_path)._connect()) as c,c: c.execute("UPDATE beta_invitations SET active=0,revoked_at=? WHERE rowid=?",(datetime.now(timezone.utc).isoformat(),invitation_id));c.execute("INSERT INTO admin_audit_log(actor_id,action) VALUES(?,?)",(actor_id,"invitation_revoked"))

def registration_allowed(code,database_path,development_mode=False):
 """Return a neutral result before account creation; no invitation is consumed here."""
 with closing(SQLiteRepository(database_path)._connect()) as c:
  settings=c.execute("SELECT * FROM beta_settings WHERE id=1").fetchone(); count=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
 if not settings["registrations_open"]: return False,"Inscriptions momentanément fermées."
 if count>=settings["max_participants"]: return False,"La capacité bêta est atteinte."
 if settings["invitation_required"] and not development_mode:
  return (validate_invitation(code or "",database_path)=="active", "Code d'invitation invalide ou indisponible.")
 return True,""

def consume_invitation(code,database_path):
 """Atomically consume exactly one active invitation after successful registration."""
 with closing(SQLiteRepository(database_path)._connect()) as c,c:
  row=c.execute("SELECT rowid,* FROM beta_invitations WHERE code_hash=?",(_hash(code),)).fetchone()
  if invitation_status(row)!="active": return False
  return c.execute("UPDATE beta_invitations SET uses_count=uses_count+1 WHERE rowid=? AND uses_count<max_uses",(row[0],)).rowcount==1

def update_beta_settings(actor,database_path,registrations_open,invitation_required,max_participants,banner_active,message):
 _admin(actor,database_path)
 if not 1 <= int(max_participants) <= 10_000 or not message.strip(): raise ValueError("Limite ou message invalide.")
 with closing(SQLiteRepository(database_path)._connect()) as c,c:
  c.execute("UPDATE beta_settings SET registrations_open=?,invitation_required=?,max_participants=?,banner_active=?,message=? WHERE id=1",(int(registrations_open),int(invitation_required),int(max_participants),int(banner_active),message.strip()))
  c.execute("INSERT INTO admin_audit_log(actor_id,action,metadata) VALUES(?,?,?)",(actor,"beta_settings_updated",'{"confirmed":true}'))

def _admin(actor,database_path):
 with closing(SQLiteRepository(database_path)._connect()) as c: row=c.execute("SELECT role FROM users WHERE id=?",(actor,)).fetchone()
 if not row or row[0]!="admin": raise PermissionError("Accès refusé")
def invitations(actor,database_path,status=None,label=None,page=1,size=20,sort="created_at DESC"):
 _admin(actor,database_path);where=[];p=[]
 if label: where.append("label LIKE ?");p.append("%"+label+"%")
 allowed={"created_at DESC","expires_at ASC","uses_count DESC"};sort=sort if sort in allowed else "created_at DESC"
 with closing(SQLiteRepository(database_path)._connect()) as c:
  rows=c.execute("SELECT rowid,label,created_at,expires_at,uses_count,max_uses,revoked_at,creator_id,active FROM beta_invitations"+(" WHERE "+" AND ".join(where) if where else "")+" ORDER BY "+sort+" LIMIT ? OFFSET ?",(*p,size,(page-1)*size)).fetchall()
 return [dict(x)|{"status":invitation_status(x)} for x in rows if not status or invitation_status(x)==status]
def _safe(v): return "'"+str(v) if str(v)[:1] in "=+-@" else v
def export_invitations(actor,database_path):
 rows=invitations(actor,database_path,size=10000);o=StringIO();w=csv.DictWriter(o,fieldnames=["id","label","status","created_at","expires_at","uses_count","max_uses","revoked_at","creator_id"]);w.writeheader();[w.writerow({k:_safe(x.get(k)) for k in w.fieldnames}) for x in rows];return o.getvalue()
def admin_log(actor,database_path,page=1,size=20):
 _admin(actor,database_path)
 with closing(SQLiteRepository(database_path)._connect()) as c: rows=c.execute("SELECT id,actor_id,action,created_at FROM admin_audit_log ORDER BY created_at DESC LIMIT ? OFFSET ?",(size,(page-1)*size)).fetchall()
 return [dict(x) for x in rows]
def export_admin_log(actor,database_path):
 rows=admin_log(actor,database_path,size=10000);o=StringIO();w=csv.DictWriter(o,fieldnames=["id","created_at","actor_id","action"]);w.writeheader();[w.writerow({k:_safe(x[k]) for k in w.fieldnames}) for x in rows];return o.getvalue()
