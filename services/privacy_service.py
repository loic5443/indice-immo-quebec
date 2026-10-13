"""Local privacy operations; exports are user-scoped and never include password material."""
import json
from contextlib import closing
from data.database import list_analyses
from repositories.sqlite_repository import SQLiteRepository

def export_user_data(user_id, database_path):
    user=SQLiteRepository(database_path).get_user_by_id(user_id)
    if not user: return None
    for field in ("password_hash", "password_salt", "failed_login_count", "locked_until"): user.pop(field, None)
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        row = connection.execute("SELECT criteria_json FROM investment_criteria WHERE user_id=?", (user_id,)).fetchone()
    criteria = json.loads(row[0]) if row else {}
    return json.dumps({"profile":user,"analyses":list_analyses(user_id,database_path),"investment_criteria":criteria}, ensure_ascii=False, indent=2)

def delete_account(user_id, database_path):
    repository=SQLiteRepository(database_path)
    with closing(repository._connect()) as connection, connection:
        # Billing accounts must first be resolved by support; deletion must never
        # leave a recurring payment active without an owning app account.
        if connection.execute("SELECT 1 FROM billing_accounts WHERE user_id=?", (user_id,)).fetchone():
            return False
        return connection.execute("DELETE FROM users WHERE id=?",(user_id,)).rowcount == 1
