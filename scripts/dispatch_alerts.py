"""Run one privacy-preserving alert-email check for opted-in ImmoRadar accounts.

This script is safe to run repeatedly: delivery fingerprints prevent duplicate
messages. It emits aggregates only and never prints users, dossiers, emails,
addresses, or financial information.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.database import DATABASE_PATH, initialize_database
from services.alert_delivery_service import deliver_alerts_for_all_users


def main() -> int:
    initialize_database(DATABASE_PATH)
    results = deliver_alerts_for_all_users(DATABASE_PATH)
    statuses = Counter(result.status for result in results)
    delivered = sum(result.delivered for result in results)
    print(f"Comptes vérifiés : {len(results)}")
    print(f"Nouvelles alertes livrées : {delivered}")
    print("Statuts : " + ", ".join(f"{key}={value}" for key, value in sorted(statuses.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
