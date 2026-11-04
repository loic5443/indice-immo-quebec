CREATE TABLE creator_profiles (
 code TEXT PRIMARY KEY, user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
 display_name TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('creator','house')),
 accepted_at INTEGER NOT NULL, terms_version TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
INSERT INTO creator_profiles VALUES ('loic',NULL,'Cenlio','house',0,'2026-11-04',1);
CREATE TABLE creator_referrals (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 creator_code TEXT NOT NULL REFERENCES creator_profiles(code) ON DELETE RESTRICT,
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
);
CREATE TABLE creator_commissions (
 id TEXT PRIMARY KEY, creator_code TEXT NOT NULL REFERENCES creator_profiles(code) ON DELETE RESTRICT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 mode TEXT NOT NULL CHECK(mode IN ('test','live')), customer_id TEXT NOT NULL,
 subscription_id TEXT NOT NULL, invoice_id TEXT NOT NULL UNIQUE,
 amount_cents INTEGER NOT NULL CHECK(amount_cents=1000), created_at INTEGER NOT NULL,
 available_at INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','paid','review','void')),
 paid_at INTEGER, payment_reference TEXT, UNIQUE(mode,user_id), UNIQUE(mode,customer_id)
);
CREATE INDEX creator_commissions_owner ON creator_commissions(creator_code,mode,created_at);
