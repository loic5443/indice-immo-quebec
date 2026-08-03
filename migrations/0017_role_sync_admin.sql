CREATE TABLE IF NOT EXISTS role_index_entries (territory_code TEXT PRIMARY KEY, municipality TEXT NOT NULL, source_url TEXT NOT NULL, source_updated_at TEXT NOT NULL, index_synced_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS role_territory_settings (territory_code TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1, removed_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS role_sync_history (id INTEGER PRIMARY KEY, territory_code TEXT NOT NULL, action TEXT NOT NULL, outcome TEXT NOT NULL, checksum TEXT, imported_units INTEGER, detail TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_role_index_name ON role_index_entries(municipality);
CREATE INDEX IF NOT EXISTS idx_role_sync_territory ON role_sync_history(territory_code, created_at DESC);
