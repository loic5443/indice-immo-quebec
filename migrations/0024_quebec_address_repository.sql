-- Provincial public-address cache. It stores only the RQA fields needed for
-- consented address suggestions; no owner, assessment, user or dossier data.
CREATE TABLE IF NOT EXISTS rqa_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL CHECK(status IN ('running', 'ready', 'failed', 'unchanged')),
    checksum TEXT NOT NULL,
    source_url TEXT NOT NULL,
    imported_rows INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS rqa_active_import (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    import_id INTEGER,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(import_id) REFERENCES rqa_imports(id)
);

CREATE TABLE IF NOT EXISTS rqa_addresses (
    import_id INTEGER NOT NULL,
    address_id TEXT NOT NULL,
    address_text TEXT NOT NULL,
    civic_number TEXT,
    unit TEXT,
    street_name TEXT NOT NULL,
    municipality TEXT NOT NULL,
    municipality_code TEXT,
    postal_code TEXT,
    address_search_key TEXT NOT NULL,
    street_search_key TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    PRIMARY KEY(import_id, address_id),
    FOREIGN KEY(import_id) REFERENCES rqa_imports(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rqa_address_prefix ON rqa_addresses(import_id, active, address_search_key);
CREATE INDEX IF NOT EXISTS idx_rqa_street_prefix ON rqa_addresses(import_id, active, street_search_key);

INSERT OR IGNORE INTO data_sources (source_id, name, official_url, license_summary, refresh_frequency, status, enabled)
VALUES (
    'quebec_address_repository',
    'Référentiel québécois des adresses (RQA)',
    'https://diffusion.mern.gouv.qc.ca/diffusion/RGQ/Vectoriel/Theme/Local/RQA/CSV/RQA_CSV.zip',
    'CC BY 4.0 — MRNF / Données Québec',
    'monthly',
    'official',
    1
);
