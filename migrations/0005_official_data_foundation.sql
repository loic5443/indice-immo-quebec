CREATE TABLE IF NOT EXISTS data_sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    official_url TEXT NOT NULL,
    license_summary TEXT NOT NULL,
    refresh_frequency TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    FOREIGN KEY(source_id) REFERENCES data_sources(source_id)
);

CREATE TABLE IF NOT EXISTS geographies (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    source_run_id INTEGER NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    geography_code TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    published_at TEXT,
    source_url TEXT NOT NULL,
    classification TEXT NOT NULL,
    quality_status TEXT NOT NULL,
    quality_reason TEXT,
    content_hash TEXT NOT NULL UNIQUE,
    FOREIGN KEY(source_id) REFERENCES data_sources(source_id),
    FOREIGN KEY(source_run_id) REFERENCES source_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_market_observations_latest ON market_observations(source_id, metric, quality_status, observed_at DESC);
ALTER TABLE analyses ADD COLUMN market_context_json TEXT NOT NULL DEFAULT '[]';
