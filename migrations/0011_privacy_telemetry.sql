ALTER TABLE privacy_events ADD COLUMN event_version TEXT NOT NULL DEFAULT '1';
ALTER TABLE privacy_events ADD COLUMN outcome_code TEXT NOT NULL DEFAULT 'ok';
ALTER TABLE privacy_events ADD COLUMN idempotency_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS privacy_events_idempotency ON privacy_events(idempotency_key) WHERE idempotency_key IS NOT NULL;
