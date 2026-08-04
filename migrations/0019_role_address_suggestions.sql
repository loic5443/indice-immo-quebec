ALTER TABLE role_assessment_units ADD COLUMN address_search_key TEXT NOT NULL DEFAULT '';
ALTER TABLE role_assessment_units ADD COLUMN street_search_key TEXT NOT NULL DEFAULT '';
UPDATE role_assessment_units
SET address_search_key = lower(replace(replace(coalesce(civic_number, '') || coalesce(street_name, ''), ' ', ''), '-', '')),
    street_search_key = lower(replace(replace(coalesce(street_name, ''), ' ', ''), '-', ''))
WHERE address_search_key = '' OR street_search_key = '';
CREATE INDEX IF NOT EXISTS idx_role_units_suggestion ON role_assessment_units(territory_code, street_search_key, civic_number);
