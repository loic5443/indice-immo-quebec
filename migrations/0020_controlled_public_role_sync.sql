INSERT OR IGNORE INTO data_sources (source_id, name, official_url, license_summary, refresh_frequency, status, enabled)
VALUES (
    'mamh_quebec_assessment_rolls',
    'Rôles d’évaluation foncière du Québec',
    'https://www.mamh.gouv.qc.ca/role/indexRole.csv',
    'CC BY 4.0',
    'Selon les publications du MAMH',
    'official',
    1
);

CREATE TABLE IF NOT EXISTS role_auto_sync_attempts (
    territory_code TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    last_attempt_at TEXT NOT NULL,
    last_success_at TEXT,
    error_code TEXT
);

CREATE TABLE IF NOT EXISTS role_auto_sync_locks (
    territory_code TEXT PRIMARY KEY,
    acquired_at TEXT NOT NULL
);
