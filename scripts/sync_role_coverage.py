"""Run a controlled batch of official Québec municipal assessment roles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.database import DATABASE_PATH, initialize_database
from services.quebec_role_coverage_service import DEFAULT_BATCH_BYTES, DEFAULT_BATCH_TERRITORIES, coverage_status, synchronize_role_coverage


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronise les rôles MAMH officiels, un territoire à la fois.")
    parser.add_argument("--confirm", action="store_true", help="Confirme le téléchargement officiel contrôlé.")
    parser.add_argument("--all", action="store_true", help="Retire la limite de territoires; conservez un budget de téléchargement.")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_TERRITORIES)
    parser.add_argument("--max-mb", type=int, default=DEFAULT_BATCH_BYTES // 1_000_000)
    arguments = parser.parse_args()
    if not arguments.confirm:
        print("Aucune synchronisation effectuée. Ajoutez --confirm après avoir vérifié l’espace et la source officielle.")
        return 2
    if arguments.max_mb < 1:
        parser.error("--max-mb doit être supérieur à zéro.")
    initialize_database(DATABASE_PATH)
    result = synchronize_role_coverage(DATABASE_PATH, territory_limit=None if arguments.all else arguments.limit, byte_budget=arguments.max_mb * 1_000_000)
    state = coverage_status(DATABASE_PATH)
    print(f"Lot {result.run_id}: {result.synchronized} synchronisé(s), {result.failed} échec(s), {result.downloaded_bytes} octets; {state['imported']}/{state['indexed']} territoires prêts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
