"""Private beta feedback with service-level access controls."""

import csv
from contextlib import closing
from io import StringIO

from repositories.sqlite_repository import SQLiteRepository


MAX_COMMENT = 2000
STATUSES = ("new", "in_review", "resolved", "closed")
ALLOWED_SORTS = {"created_at DESC", "created_at ASC", "usefulness DESC", "status ASC"}


def _require_admin(connection, actor_id: int | None) -> None:
    """Refuse administrative feedback access unless SQLite confirms the role."""

    if not isinstance(actor_id, int):
        raise PermissionError("Accès refusé")
    role = connection.execute("SELECT role FROM users WHERE id=?", (actor_id,)).fetchone()
    if not role or role[0] != "admin":
        raise PermissionError("Accès refusé")


def submit_feedback(user_id, page, category, usefulness, comment, contact, database_path):
    if not comment.strip() or len(comment) > MAX_COMMENT:
        raise ValueError("Commentaire requis (maximum 2 000 caractères).")
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute(
            "INSERT INTO feedback(user_id,page,category,comment,usefulness,contact_consent,app_version,engine_version) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (user_id, page, category, comment.strip(), usefulness, int(contact), "0.6-beta", "ImmoEngine 1.1"),
        )


def list_feedback(
    user_id,
    database_path,
    is_admin=False,
    category=None,
    status=None,
    minimum_note=None,
    query=None,
    page=1,
    page_size=20,
    sort="created_at DESC",
):
    """Read only the caller's feedback, unless SQLite confirms an admin role.

    Filters and pagination are applied by SQLite so unneeded comments are
    never loaded before the access scope is established.
    """

    if not isinstance(user_id, int):
        raise PermissionError("Accès refusé")
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    sort = sort if sort in ALLOWED_SORTS else "created_at DESC"
    clauses: list[str] = []
    params: list[object] = []
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        if is_admin:
            _require_admin(connection, user_id)
        else:
            clauses.append("user_id=?")
            params.append(user_id)
        if category:
            clauses.append("category=?")
            params.append(category)
        if status:
            clauses.append("status=?")
            params.append(status)
        if minimum_note:
            clauses.append("usefulness>=?")
            params.append(minimum_note)
        if query:
            escaped_query = str(query).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("comment LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped_query}%")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = connection.execute(
            "SELECT id,page,category,usefulness,comment,status,created_at FROM feedback"
            f"{where} ORDER BY {sort} LIMIT ? OFFSET ?",
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()
    return [dict(row) for row in rows]


def update_status(actor_id, feedback_id, status, note, database_path):
    if status not in STATUSES:
        raise ValueError("Statut invalide")
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        _require_admin(connection, actor_id)
        connection.execute(
            "UPDATE feedback SET status=?,admin_note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, note[:1000], feedback_id),
        )
        connection.execute(
            "INSERT INTO feedback_audit(feedback_id,actor_id,action) VALUES(?,?,?)",
            (feedback_id, actor_id, "status_changed"),
        )


def export_feedback_csv(user_id, database_path):
    rows = list_feedback(user_id, database_path, True)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "created_at", "category", "status", "usefulness", "page", "comment"])
    writer.writeheader()
    for row in rows:
        sanitized = {
            key: ("'" + str(value) if isinstance(value, str) and value[:1] in "=+-@" else value)
            for key, value in row.items()
        }
        writer.writerow(sanitized)
    return output.getvalue()
