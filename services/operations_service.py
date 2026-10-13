"""One safe operational cycle: private backup and consented alert delivery."""
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from providers.brevo_email import delivery_status
from services.alert_delivery_service import deliver_alerts_for_all_users
from services.backup_service import backup_database


def run_operations(database_path, backup_directory, *, environment=None, deliver=deliver_alerts_for_all_users, now=None):
    env = os.environ if environment is None else environment
    now = time.time() if now is None else now
    # Results contain aggregate categorical data only, no account or dossier.
    result = {"backup": "disabled", "alerts": "disabled"}
    if env.get("IMMORADAR_BACKUPS_ENABLED") == "1":
        stamp = datetime.fromtimestamp(now, timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = Path(backup_directory) / f"immoradar-{stamp}-{uuid4().hex[:8]}.sqlite"
        try:
            backup_database(database_path, destination)
            result["backup"] = "verified"
        except Exception:
            result["backup"] = "failed"
    if delivery_status(env) == "ready":
        try:
            outcomes = deliver(database_path, environment=env)
            result["alerts"] = dict(Counter(outcome.status for outcome in outcomes))
            result["delivered"] = sum(outcome.delivered for outcome in outcomes)
        except Exception:
            result["alerts"] = "failed"
    return result
