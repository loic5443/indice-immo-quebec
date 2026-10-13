"""Optional scheduled app maintenance; no credentials or user data in logs."""
import json
import os
from pathlib import Path
from threading import Event

from data.database import DATABASE_PATH, initialize_database
from services.operations_service import run_operations


def main():
    if os.environ.get("IMMORADAR_OPERATIONS_ENABLED") != "1":
        print(json.dumps({"operations": "disabled"}))
        return 0
    initialize_database(DATABASE_PATH)
    interval = max(3600, min(86400, int(os.environ.get("IMMORADAR_OPERATIONS_INTERVAL_SECONDS", "86400"))))
    directory = Path(os.environ.get("IMMORADAR_BACKUP_DIRECTORY", str(DATABASE_PATH.parent / "backups")))
    stop = Event()
    try:
        while not stop.is_set():
            print(json.dumps(run_operations(DATABASE_PATH, directory), ensure_ascii=False), flush=True)
            stop.wait(interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
