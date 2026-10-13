"""Configuration diagnostics only: no network calls, no secret values printed."""
import json
import os
from pathlib import Path

from data.database import DATABASE_PATH
from migrations.runner import applied_migrations, MIGRATIONS_DIRECTORY
from services.backup_service import verify_backup
from services.billing_service import BillingError, billing_config
from services.password_recovery_service import recovery_ready


def check_readiness(database_path, environment=None):
    env = os.environ if environment is None else environment
    report = {"database": "not_available", "migrations": "not_checked", "billing": "disabled",
              "account_recovery": "configured" if recovery_ready(env) else "not_configured",
              "scheduled_operations": "configured" if env.get("IMMORADAR_OPERATIONS_ENABLED") == "1" else "disabled"}
    try:
        verify_backup(database_path)
        report["database"] = "verified"
        expected = [file.stem.split("_", 1)[0] for file in sorted(MIGRATIONS_DIRECTORY.glob("[0-9][0-9][0-9][0-9]_*.sql"))]
        report["migrations"] = "current" if applied_migrations(database_path) == expected else "pending"
    except Exception:
        report["database"] = "unavailable_or_invalid"
    try:
        config = billing_config(env)
        if config:
            report["billing"] = "configured_" + config.mode
    except BillingError:
        report["billing"] = "incomplete_configuration"
    report["scope"] = "Local configuration only; HTTPS, provider delivery and payment still require integration testing."
    return report


if __name__ == "__main__":
    print(json.dumps(check_readiness(DATABASE_PATH), ensure_ascii=False, indent=2))
