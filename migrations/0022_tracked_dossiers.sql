-- A follow selection stores only an owner-scoped, non-reversible dossier key.
-- It does not store an address, financial amount, or notification destination.
CREATE TABLE IF NOT EXISTS tracked_dossiers (
    user_id INTEGER NOT NULL,
    dossier_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, dossier_fingerprint),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tracked_dossiers_user ON tracked_dossiers(user_id);
