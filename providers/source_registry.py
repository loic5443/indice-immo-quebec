"""Versioned registry loader. The JSON file is the human-reviewable source of truth."""

import json
from pathlib import Path


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "docs" / "source_registry.json"


def load_source_registry() -> dict[str, dict[str, object]]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {item["source_id"]: item for item in data["sources"]}


def integrated_sources() -> list[dict[str, object]]:
    return [source for source in load_source_registry().values() if source["status"] == "integrated"]
