"""Private beta invitations: opaque codes are shown once and stored only as hashes."""
import hashlib,secrets
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
