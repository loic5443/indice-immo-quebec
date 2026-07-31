"""Source orchestration: validate, quarantine failures, and retain the last valid cache."""

from typing import Any

from domain.market_data import MarketObservation
from providers.official_data import OfficialDataProvider, ProviderError
from providers.source_registry import load_source_registry
from repositories.market_data_repository import MarketDataRepository
from services.data_quality import freshness_label, validate_observation


def refresh_source(database_path: str, provider: OfficialDataProvider) -> list[MarketObservation]:
    from services.diagnostics_service import source_enabled
    if not source_enabled(provider.source_id, database_path):
        return []
    registry = load_source_registry()
    source = registry[provider.source_id]
    repository = MarketDataRepository(database_path)
    repository.sync_source(source)
    run_id = repository.start_run(provider.source_id)
    try:
        observations = provider.fetch()
    except ProviderError as error:
        repository.finish_run(run_id, "failed", str(error))
        return []
    valid: list[MarketObservation] = []
    for observation in observations:
        errors = validate_observation(observation)
        if errors:
            repository.store_observation(observation, run_id, "quarantined", "; ".join(errors))
        else:
            repository.store_observation(observation, run_id)
            valid.append(observation)
    repository.finish_run(run_id, "success" if valid else "quarantined")
    return valid


def cached_policy_rate(database_path: str) -> dict[str, Any] | None:
    row = MarketDataRepository(database_path).latest_valid("bank_of_canada_valet", "policy_rate")
    if row:
        row["freshness"] = freshness_label(row["observed_at"])
    return row


def market_context_snapshot(database_path: str) -> list[dict[str, Any]]:
    """Return real cached context only; this does not affect ImmoEngine scoring."""
    row = cached_policy_rate(database_path)
    if not row:
        return []
    return [{key: row[key] for key in ("source_id", "metric", "value", "unit", "geography_code", "observed_at", "retrieved_at", "source_url", "freshness")}]
