CREATE TABLE billing_accounts (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
    customer_id TEXT NOT NULL UNIQUE,
    mode TEXT NOT NULL DEFAULT 'test' CHECK(mode IN ('test', 'live')),
    subscription_id TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'none',
    access_until INTEGER NOT NULL DEFAULT 0,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE billing_checkouts (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    request_key TEXT NOT NULL UNIQUE,
    session_id TEXT UNIQUE,
    created_at INTEGER NOT NULL
);
CREATE TABLE billing_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at INTEGER NOT NULL
);
