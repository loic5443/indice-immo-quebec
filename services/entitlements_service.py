"""Single source of truth for rights and atomic monthly free-estimation usage."""
import os
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo

from repositories.sqlite_repository import SQLiteRepository


PREMIUM_FEATURES = {"alerts", "reports", "unlimited_estimations", "advanced_comparisons"}


def can_use(user, feature):
    return user.get("role") == "admin" or user.get("plan") == "premium" or feature not in PREMIUM_FEATURES


def quota_is_enforced(database_path) -> bool:
    # Launching commercial billing also enables its advertised free allowance.
    if os.environ.get("IMMORADAR_BILLING_ENABLED") == "1":
        return True
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        row = connection.execute("SELECT quota_enforced FROM beta_settings WHERE id=1").fetchone()
    return bool(row and row[0])


def quota_status(user_id, user, database_path, now=None):
    if can_use(user, "unlimited_estimations"):
        return {"remaining": None, "label": "Illimité"}
    now = now or datetime.now(ZoneInfo("America/Toronto"))
    period = now.strftime("%Y-%m")
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        used = connection.execute("SELECT COUNT(*) FROM monthly_estimation_usage WHERE user_id=? AND period_key=?", (user_id, period)).fetchone()[0]
    remaining = max(0, 1 - used)
    return {"remaining": remaining, "label": f"{remaining} estimation complète restante ce mois-ci", "period": period}


def consume_estimation(user_id, user, database_path, key):
    if can_use(user, "unlimited_estimations"):
        return True
    period = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m")
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM monthly_estimation_usage WHERE user_id=? AND period_key=? AND idempotency_key=?", (user_id, period, key)).fetchone():
            return True
        used = connection.execute("SELECT COUNT(*) FROM monthly_estimation_usage WHERE user_id=? AND period_key=?", (user_id, period)).fetchone()[0]
        if used >= 1:
            return False
        connection.execute("INSERT INTO monthly_estimation_usage(user_id,period_key,idempotency_key) VALUES(?,?,?)", (user_id, period, key))
    return True
