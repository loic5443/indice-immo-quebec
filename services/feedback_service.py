"""User feedback stored locally, scoped to its author or an administrator."""
from contextlib import closing
from repositories.sqlite_repository import SQLiteRepository

MAX_COMMENT=2000
def submit_feedback(user_id,page,category,usefulness,comment,contact,database_path):
 if not comment.strip() or len(comment)>MAX_COMMENT: raise ValueError("Commentaire requis (maximum 2 000 caractères).")
 with closing(SQLiteRepository(database_path)._connect()) as c,c:
  c.execute("INSERT INTO feedback(user_id,page,category,comment,usefulness,contact_consent,app_version,engine_version) VALUES(?,?,?,?,?,?,?,?)",(user_id,page,category,comment.strip(),usefulness,int(contact),"0.6-beta","ImmoEngine 1.1"))
def list_feedback(user_id,database_path,is_admin=False):
 with closing(SQLiteRepository(database_path)._connect()) as c:
  rows=c.execute("SELECT id,page,category,usefulness,comment,status,created_at FROM feedback" + ("" if is_admin else " WHERE user_id=?"),( ) if is_admin else (user_id,)).fetchall()
 return [dict(x) for x in rows]
