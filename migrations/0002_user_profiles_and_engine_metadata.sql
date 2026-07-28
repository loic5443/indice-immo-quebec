ALTER TABLE users ADD COLUMN user_type TEXT NOT NULL DEFAULT 'Investisseur';
ALTER TABLE users ADD COLUMN investment_horizon TEXT NOT NULL DEFAULT '2 à 5 ans';
ALTER TABLE users ADD COLUMN risk_tolerance TEXT NOT NULL DEFAULT 'Modéré';

ALTER TABLE analyses ADD COLUMN engine_version TEXT NOT NULL DEFAULT 'ImmoEngine 0.1.0-preparation';
ALTER TABLE analyses ADD COLUMN data_provenance TEXT NOT NULL DEFAULT 'Hypothèses saisies par l''utilisateur; calculs financiers ImmoRadar; aucune estimation de valeur.';
