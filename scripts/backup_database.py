"""Run: python -m scripts.backup_database --destination /private/new-backup.sqlite"""
import argparse
import json

from data.database import DATABASE_PATH
from services.backup_service import BackupError, backup_database, verify_backup


def main():
    parser = argparse.ArgumentParser(description="Sauvegarde SQLite cohérente et vérifiée")
    parser.add_argument("--source", default=str(DATABASE_PATH))
    parser.add_argument("--destination")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.verify_only and not args.destination:
        parser.error("--destination est requis pour créer une sauvegarde")
    try:
        metadata = verify_backup(args.source) if args.verify_only else backup_database(args.source, args.destination)
    except (BackupError, OSError):
        print(json.dumps({"status": "failed", "reason": "backup_unavailable_or_invalid"}))
        return 1
    print(json.dumps({"status": "verified", **metadata}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
