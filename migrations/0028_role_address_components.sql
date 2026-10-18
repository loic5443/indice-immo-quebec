ALTER TABLE role_assessment_units ADD COLUMN civic_number_end TEXT;
CREATE INDEX IF NOT EXISTS idx_role_units_upper_civic ON role_assessment_units(territory_code, street_search_key, civic_number_end);
ALTER TABLE role_territory_imports ADD COLUMN address_parser_version INTEGER NOT NULL DEFAULT 1;
