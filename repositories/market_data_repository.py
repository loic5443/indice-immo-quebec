"""SQLite persistence for source runs and immutable external observations."""

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from domain.market_data import MarketObservation


class MarketDataRepository:
    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def sync_source(self, source: dict[str, object]) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("""INSERT INTO data_sources (source_id, name, official_url, license_summary, refresh_frequency, status)
                VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET
                name=excluded.name, official_url=excluded.official_url, license_summary=excluded.license_summary,
                refresh_frequency=excluded.refresh_frequency, status=excluded.status""", (
                source["source_id"], source["name"], source["official_url"], source["license_summary"],
                source["refresh_frequency"], source["status"],
            ))

    def start_run(self, source_id: str) -> int:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("INSERT INTO source_runs (source_id, status) VALUES (?, 'running')", (source_id,))
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, message: str | None = None) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("UPDATE source_runs SET status=?, message=?, finished_at=CURRENT_TIMESTAMP WHERE id=?", (status, message, run_id))

    def store_observation(self, observation: MarketObservation, run_id: int, status: str = "valid", reason: str | None = None) -> None:
        content = "|".join((observation.source_id, observation.metric, str(observation.value), observation.unit, observation.geography_code, observation.observed_at))
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with closing(self._connect()) as connection, connection:
            connection.execute("""INSERT OR IGNORE INTO market_observations (
                source_id, source_run_id, metric, value, unit, geography_code, observed_at, retrieved_at,
                published_at, source_url, classification, quality_status, quality_reason, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                observation.source_id, run_id, observation.metric, observation.value, observation.unit,
                observation.geography_code, observation.observed_at, observation.retrieved_at,
                observation.published_at, observation.source_url, observation.classification, status, reason, content_hash,
            ))

    def latest_valid(self, source_id: str, metric: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute("""SELECT * FROM market_observations WHERE source_id=? AND metric=? AND quality_status='valid'
                ORDER BY observed_at DESC, id DESC LIMIT 1""", (source_id, metric)).fetchone()
        return dict(row) if row else None
