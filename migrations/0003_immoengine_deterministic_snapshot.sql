ALTER TABLE analyses ADD COLUMN user_profile TEXT NOT NULL DEFAULT 'Investisseur locatif';
ALTER TABLE analyses ADD COLUMN immo_score REAL;
ALTER TABLE analyses ADD COLUMN confidence_index REAL;
ALTER TABLE analyses ADD COLUMN engine_verdict TEXT;
ALTER TABLE analyses ADD COLUMN positive_factors_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE analyses ADD COLUMN negative_factors_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE analyses ADD COLUMN missing_data_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE analyses ADD COLUMN recommended_checks_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE analyses ADD COLUMN immodna_json TEXT NOT NULL DEFAULT '{}';

UPDATE users SET user_type = 'Premier acheteur' WHERE user_type = 'Curieux';
UPDATE users SET user_type = 'Investisseur locatif' WHERE user_type = 'Investisseur';
UPDATE users SET user_type = 'Propriétaire' WHERE user_type = 'Propriétaire occupant';
UPDATE users SET user_type = 'Courtier ou analyste' WHERE user_type = 'Courtier / professionnel';
