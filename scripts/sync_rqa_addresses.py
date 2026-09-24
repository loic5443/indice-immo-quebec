"""Explicit local synchronization for Québec-wide public address suggestions.

The RQA archive is downloaded only after a human deliberately confirms this
command.  It is temporary; the ZIP is never kept in the repository.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The script is deliberately runnable with ``python scripts/...`` from the
# repository root without requiring package installation.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.database import DATABASE_PATH, initialize_database
from services.quebec_address_repository import rqa_status, synchronize_rqa_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronise le RQA officiel dans le cache local ImmoRadar.")
    parser.add_argument("--confirm", action="store_true", help="Confirme le téléchargement officiel provincial temporaire.")
    parser.add_argument("--archive", type=Path, help="Archive officielle déjà téléchargée temporairement; évite un nouveau téléchargement.")
    arguments = parser.parse_args()
    if not arguments.confirm:
        print("Aucune synchronisation effectuée. Relancez avec --confirm après avoir vérifié l’espace disque.")
        return 2

    initialize_database(DATABASE_PATH)
    if arguments.archive:
        from services.quebec_address_repository import import_rqa_archive
        result = import_rqa_archive(arguments.archive, DATABASE_PATH)
    else:
        result = synchronize_rqa_snapshot(DATABASE_PATH)
    status = rqa_status(DATABASE_PATH)
    print(f"Synchronisation RQA : {result.status}; adresses publiques actives : {status['addresses']}; archive temporaire supprimée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
