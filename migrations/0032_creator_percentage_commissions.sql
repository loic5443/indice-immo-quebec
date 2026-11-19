-- Preserve every existing amount and uniqueness rule; allow variable commissions.
CREATE TABLE creator_commissions_v2 (
 id TEXT PRIMARY KEY, creator_code TEXT NOT NULL REFERENCES creator_profiles(code) ON DELETE RESTRICT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 mode TEXT NOT NULL CHECK(mode IN ('test','live')), customer_id TEXT NOT NULL,
 subscription_id TEXT NOT NULL, invoice_id TEXT NOT NULL UNIQUE,
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0), created_at INTEGER NOT NULL,
 available_at INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','paid','review','void')),
 paid_at INTEGER, payment_reference TEXT, UNIQUE(mode,user_id), UNIQUE(mode,customer_id)
);
INSERT INTO creator_commissions_v2 SELECT * FROM creator_commissions;
DROP TABLE creator_commissions;
ALTER TABLE creator_commissions_v2 RENAME TO creator_commissions;
CREATE INDEX creator_commissions_owner ON creator_commissions(creator_code,mode,created_at);
