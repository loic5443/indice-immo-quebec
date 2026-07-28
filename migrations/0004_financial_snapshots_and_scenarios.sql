ALTER TABLE analyses ADD COLUMN financial_inputs_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE analyses ADD COLUMN scenarios_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE analyses ADD COLUMN resilience_json TEXT NOT NULL DEFAULT '{}';
