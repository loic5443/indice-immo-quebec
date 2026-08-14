"""Saved-analysis service with ImmoEngine traceability metadata."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from providers.data_provenance import IMMOENGINE_METADATA
from domain.immoengine import ImmoEngineResult
from repositories.sqlite_repository import SQLiteRepository


def save_user_analysis(
    user_id: int, property_name: str, values: dict[str, Any], database_path: Path | str,
    profile: str = "Investisseur locatif", engine_result: ImmoEngineResult | None = None,
) -> int:
    """Persist user assumptions and calculated outputs; no value estimate is produced."""
    snapshot = engine_result.to_snapshot() if engine_result else {}
    payload: dict[str, Any] = {
        **values,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "engine_version": IMMOENGINE_METADATA.version,
        "data_provenance": IMMOENGINE_METADATA.data_provenance,
        "user_profile": profile,
        "immo_score": snapshot.get("score"),
        "confidence_index": snapshot.get("confidence_index"),
        "engine_verdict": snapshot.get("verdict"),
        "positive_factors_json": json.dumps(snapshot.get("positive_factors", []), ensure_ascii=False),
        "negative_factors_json": json.dumps(snapshot.get("negative_factors", []), ensure_ascii=False),
        "missing_data_json": json.dumps(snapshot.get("missing_data", []), ensure_ascii=False),
        "recommended_checks_json": json.dumps(snapshot.get("recommended_checks", []), ensure_ascii=False),
        "immodna_json": json.dumps(snapshot.get("dimensions", {}), ensure_ascii=False),
        "financial_inputs_json": json.dumps(values.get("financial_inputs", {}), ensure_ascii=False),
        "scenarios_json": json.dumps(values.get("scenarios", []), ensure_ascii=False),
        "resilience_json": json.dumps(values.get("resilience", {}), ensure_ascii=False),
        # Informative provenance snapshot; it does not enter ImmoEngine's score or verdict.
        "market_context_json": json.dumps(values.get("market_context", []), ensure_ascii=False),
        "immovalue_json": json.dumps(values.get("immovalue", {}), ensure_ascii=False),
        # Public fiscal information is retained as a small, address-free snapshot.
        # It remains separate from ImmoValue and from financial assumptions.
        "official_role_snapshot_json": json.dumps(values.get("official_role_snapshot", {}), ensure_ascii=False),
    }
    return SQLiteRepository(database_path).save_analysis(user_id, property_name.strip(), payload)


def list_user_analyses(user_id: int, database_path: Path | str) -> list[dict[str, Any]]:
    return SQLiteRepository(database_path).list_analyses(user_id)


def get_user_analyses_for_comparison(
    user_id: int, analysis_a_id: int, analysis_b_id: int, database_path: Path | str,
) -> list[dict[str, Any]]:
    """Load two immutable saved snapshots, enforcing ownership in SQLite."""
    return SQLiteRepository(database_path).get_owned_analyses_for_comparison(
        user_id, analysis_a_id, analysis_b_id,
    )


def count_user_analyses(user_id: int, database_path: Path | str) -> int:
    return SQLiteRepository(database_path).count_analyses(user_id)


def delete_user_analysis(user_id: int, analysis_id: int, database_path: Path | str) -> bool:
    return SQLiteRepository(database_path).delete_analysis(user_id, analysis_id)


def toggle_user_analysis_favorite(user_id: int, analysis_id: int, database_path: Path | str) -> bool:
    return SQLiteRepository(database_path).toggle_favorite(user_id, analysis_id)
