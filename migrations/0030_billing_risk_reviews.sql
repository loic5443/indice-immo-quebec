CREATE TABLE billing_risk_reviews (
    event_id TEXT NOT NULL,
    subscription_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER,
    resolved_by INTEGER,
    PRIMARY KEY(event_id, subscription_id)
);
