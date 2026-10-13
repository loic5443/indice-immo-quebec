ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0;
CREATE TABLE password_reset_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL,
    used_at INTEGER,
    created_at INTEGER NOT NULL
);
CREATE TABLE auth_attempt_windows (
    identity_hash TEXT NOT NULL,
    purpose TEXT NOT NULL,
    window_start INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(identity_hash, purpose)
);
CREATE TABLE investment_criteria (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    criteria_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
