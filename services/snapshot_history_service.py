"""Group immutable saved analyses into a safe, readable dossier timeline."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SnapshotPosition:
    """One persisted analysis positioned within its exact dossier history."""

    position: int
    total: int
    is_latest: bool
    snapshots: tuple[dict[str, Any], ...]


def canonical_dossier_key(name: object) -> str:
    """Group only deliberately identical dossier names, never guessed addresses."""

    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(character for character in text.casefold() if not unicodedata.combining(character))
    return " ".join(text.split())


def snapshot_positions(analyses: list[dict[str, Any]]) -> dict[int, SnapshotPosition]:
    """Return latest-first history metadata without loading any other account's data.

    ``analyses`` must already be obtained through the owner-scoped repository
    query.  Different names are intentionally never merged by approximation.
    """

    grouped: dict[str, list[dict[str, Any]]] = {}
    for analysis in analyses:
        identifier = analysis.get("id")
        key = canonical_dossier_key(analysis.get("property_name"))
        if not isinstance(identifier, int) or not key:
            continue
        grouped.setdefault(key, []).append(analysis)

    result: dict[int, SnapshotPosition] = {}
    for snapshots in grouped.values():
        ordered = tuple(sorted(
            snapshots,
            key=lambda item: (str(item.get("created_at") or ""), int(item.get("id") or 0)),
            reverse=True,
        ))
        for index, snapshot in enumerate(ordered, start=1):
            result[int(snapshot["id"])] = SnapshotPosition(
                position=index,
                total=len(ordered),
                is_latest=index == 1,
                snapshots=ordered,
            )
    return result
