"""Feedback access is enforced in the service, not only by the interface."""
import csv
from contextlib import closing
from io import StringIO
from repositories.sqlite_repository import SQLiteRepository
MAX_COMMENT=2000; STATUSES=("new","in_review","resolved","closed")
def submit_feedback(user_id,page,category,usefulness,comment,contact,database_path):
 if not comment.strip() or len(comment)>MAX_COMMENT: raise ValueError("Commentaire requis (maximum 2 000 caractères).")
 with closing(SQLiteRepository(database_path)._connect()) as c,c:c.execute("INSERT INTO feedback(user_id,page,category,comment,usefulness,contact_consent,app_version,engine_version) VALUES(?,?,?,?,?,?,?,?)",(user_id,page,category,comment.strip(),usefulness,int(contact),"0.6-beta","ImmoEngine 1.1"))
def list_feedback(user_id,database_path,is_admin=False):
 with closing(SQLiteRepository(database_path)._connect()) as c: rows=c.execute("SELECT id,page,category,usefulness,comment,status,created_at FROM feedback"+("" if is_admin else " WHERE user_id=?"),() if is_admin else (user_id,)).fetchall()
 return [dict(x) for x in rows]
def update_status(actor_id,feedback_id,status,note,database_path):
 if status not in STATUSES: raise ValueError("Statut invalide")
 with closing(SQLiteRepository(database_path)._connect()) as c,c:
  role=c.execute("SELECT role FROM users WHERE id=?",(actor_id,)).fetchone()
  if not role or role[0]!="admin": raise PermissionError("Accès refusé")
  c.execute("UPDATE feedback SET status=?,admin_note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(status,note[:1000],feedback_id));c.execute("INSERT INTO feedback_audit(feedback_id,actor_id,action) VALUES(?,?,?)",(feedback_id,actor_id,"status_changed"))
def export_feedback_csv(user_id,database_path):
 rows=list_feedback(user_id,database_path,True); out=StringIO();w=csv.DictWriter(out,fieldnames=["id","created_at","category","status","usefulness","page","comment"]);w.writeheader()
 for row in rows:
  row={k:("'"+str(v) if isinstance(v,str) and v[:1] in "=+-@" else v) for k,v in row.items()};w.writerow(row)
 return out.getvalue()
