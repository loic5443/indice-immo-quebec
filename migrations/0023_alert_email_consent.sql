-- Alert-email consent is separate from marketing consent and defaults to off.
ALTER TABLE users ADD COLUMN alert_email_consent INTEGER NOT NULL DEFAULT 0 CHECK(alert_email_consent IN (0, 1));
ALTER TABLE users ADD COLUMN alert_email_consent_at TEXT;

-- Delivery attempts never store an email address, an address, or alert content.
CREATE TABLE IF NOT EXISTS alert_delivery_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    alert_fingerprint TEXT NOT NULL,
    channel TEXT NOT NULL CHECK(channel IN ('email')),
    outcome TEXT NOT NULL CHECK(outcome IN ('queued', 'sent', 'skipped', 'failed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, alert_fingerprint, channel),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
