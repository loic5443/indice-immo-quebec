-- Aggregate operational history for controlled province-wide role synchronization.
-- It stores no address, account, owner or assessment values.
CREATE TABLE IF NOT EXISTS role_coverage_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'stopped', 'failed')),
    requested_limit INTEGER,
    byte_budget INTEGER NOT NULL,
    scanned_territories INTEGER NOT NULL DEFAULT 0,
    synchronized_territories INTEGER NOT NULL DEFAULT 0,
    skipped_territories INTEGER NOT NULL DEFAULT 0,
    failed_territories INTEGER NOT NULL DEFAULT 0,
    downloaded_bytes INTEGER NOT NULL DEFAULT 0
);
