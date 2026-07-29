ALTER TABLE users ADD COLUMN onboarding_step INTEGER NOT NULL DEFAULT 1;
ALTER TABLE users ADD COLUMN user_objective TEXT;
ALTER TABLE users ADD COLUMN limitations_accepted INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN onboarding_completed_at TEXT;
