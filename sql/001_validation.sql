





CREATE FUNCTION is_valid_regex(p_pattern text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    PERFORM '' ~ p_pattern;
    RETURN true;
EXCEPTION WHEN invalid_regular_expression THEN
    RETURN false;
END $$;

CREATE FUNCTION is_valid_date(p_value text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF p_value !~ '^\d{4}-\d{2}-\d{2}$' THEN
        RETURN false;
    END IF;
    PERFORM p_value::date;
    RETURN true;
EXCEPTION WHEN datetime_field_overflow OR invalid_datetime_format THEN
    RETURN false;
END $$;



DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'product_code_unique' AND conrelid = 'product'::regclass) THEN ALTER TABLE product ADD CONSTRAINT product_code_unique UNIQUE (code); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'product_name_unique' AND conrelid = 'product'::regclass) THEN ALTER TABLE product ADD CONSTRAINT product_name_unique UNIQUE (name); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'product_code_format' AND conrelid = 'product'::regclass) THEN ALTER TABLE product ADD CONSTRAINT product_code_format CHECK (code ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND length(code) <= 50); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'product_name_not_blank' AND conrelid = 'product'::regclass) THEN ALTER TABLE product ADD CONSTRAINT product_name_not_blank CHECK (btrim(name) <> '' AND length(name) <= 100); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'client_name_unique' AND conrelid = 'client'::regclass) THEN ALTER TABLE client ADD CONSTRAINT client_name_unique UNIQUE (name); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'client_name_not_blank' AND conrelid = 'client'::regclass) THEN ALTER TABLE client ADD CONSTRAINT client_name_not_blank CHECK (btrim(name) <> '' AND length(name) <= 100); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'membership_unique' AND conrelid = 'membership'::regclass) THEN ALTER TABLE membership ADD CONSTRAINT membership_unique UNIQUE (user_id, product_id); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'membership_role_valid' AND conrelid = 'membership'::regclass) THEN ALTER TABLE membership ADD CONSTRAINT membership_role_valid CHECK (role IN ('manager', 'editor')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_key_unique' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_key_unique UNIQUE (product_id, key); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_key_format' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_key_format CHECK (key ~ '^[a-z][a-z0-9_]*$' AND length(key) <= 50); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_label_not_blank' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_label_not_blank CHECK (btrim(label) <> '' AND length(label) <= 100); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_type_valid' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_type_valid CHECK (field_type IN ('text', 'integer', 'decimal', 'boolean', 'date', 'choice')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_range_only_numeric' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_range_only_numeric CHECK (field_type IN ('integer', 'decimal') OR (min_value IS NULL AND max_value IS NULL)); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_min_le_max' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_min_le_max CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_choices_only_choice' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_choices_only_choice CHECK ((field_type = 'choice') = (choices IS NOT NULL)); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_choices_at_least_two' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_choices_at_least_two CHECK (choices IS NULL OR cardinality(choices) >= 2); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_pattern_only_text' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_pattern_only_text CHECK (pattern IS NULL OR field_type = 'text'); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_pattern_valid' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_pattern_valid CHECK (pattern IS NULL OR is_valid_regex(pattern)); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_boolean_optional' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_boolean_optional CHECK (field_type <> 'boolean' OR NOT required); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'schema_field_position_positive' AND conrelid = 'schema_field'::regclass) THEN ALTER TABLE schema_field ADD CONSTRAINT schema_field_position_positive CHECK (position >= 0); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'configuration_product_client_unique' AND conrelid = 'configuration'::regclass) THEN ALTER TABLE configuration ADD CONSTRAINT configuration_product_client_unique UNIQUE (product_id, client_id); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'configuration_status_valid' AND conrelid = 'configuration'::regclass) THEN ALTER TABLE configuration ADD CONSTRAINT configuration_status_valid CHECK (status IN ('active', 'disabled')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'configuration_data_is_object' AND conrelid = 'configuration'::regclass) THEN ALTER TABLE configuration ADD CONSTRAINT configuration_data_is_object CHECK (jsonb_typeof(data) = 'object'); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'configuration_version_positive' AND conrelid = 'configuration'::regclass) THEN ALTER TABLE configuration ADD CONSTRAINT configuration_version_positive CHECK (version >= 0); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'config_version_number_unique' AND conrelid = 'config_version'::regclass) THEN ALTER TABLE config_version ADD CONSTRAINT config_version_number_unique UNIQUE (configuration_id, number); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'config_version_number_positive' AND conrelid = 'config_version'::regclass) THEN ALTER TABLE config_version ADD CONSTRAINT config_version_number_positive CHECK (number >= 1); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'config_version_comment_not_blank' AND conrelid = 'config_version'::regclass) THEN ALTER TABLE config_version ADD CONSTRAINT config_version_comment_not_blank CHECK (btrim(comment) <> '' AND length(comment) <= 200); END IF; END $$;

CREATE FUNCTION config_errors(p_product_id bigint, p_data jsonb)
RETURNS TABLE (field_key text, message text)
LANGUAGE plpgsql STABLE AS $$
DECLARE
    f      schema_field;
    v      jsonb;
    t      text;
    n      numeric;
BEGIN
    IF p_data IS NULL OR jsonb_typeof(p_data) <> 'object' THEN
        field_key := NULL;
        message := 'Configuration data must be a JSON object.';
        RETURN NEXT;
        RETURN;
    END IF;

    RETURN QUERY
        SELECT k, 'Unknown key: not in the product schema.'
        FROM jsonb_object_keys(p_data) AS k
        WHERE NOT EXISTS (SELECT 1 FROM schema_field s WHERE s.product_id = p_product_id AND s.key = k);

    FOR f IN SELECT * FROM schema_field WHERE product_id = p_product_id ORDER BY position, key LOOP
        v := p_data -> f.key;
        field_key := f.key;

        IF v IS NULL OR v = 'null'::jsonb OR v = '""'::jsonb THEN
            IF f.required THEN
                message := 'This field is required.';
                RETURN NEXT;
            END IF;
            CONTINUE;
        END IF;

        t := jsonb_typeof(v);

        message := CASE f.field_type
            WHEN 'boolean' THEN
                CASE WHEN t <> 'boolean' THEN 'Must be true or false.' END
            WHEN 'integer' THEN
                CASE WHEN t <> 'number' THEN 'Must be a whole number.'
                     WHEN v::numeric <> trunc(v::numeric) THEN 'Must be a whole number.' END
            WHEN 'decimal' THEN
                CASE WHEN t <> 'number' THEN 'Must be a number.' END
            WHEN 'date' THEN
                CASE WHEN t <> 'string' THEN 'Must be a date (YYYY-MM-DD).'
                     WHEN NOT is_valid_date(v #>> '{}') THEN 'Must be a date (YYYY-MM-DD).' END
            WHEN 'choice' THEN
                CASE WHEN t <> 'string' OR NOT (v #>> '{}') = ANY (f.choices)
                     THEN 'Must be one of: ' || array_to_string(f.choices, ', ') || '.' END
            WHEN 'text' THEN
                CASE WHEN t <> 'string' THEN 'Must be text.'
                     WHEN length(v #>> '{}') > 500 THEN 'At most 500 characters.'
                     WHEN f.pattern IS NOT NULL AND (v #>> '{}') !~ f.pattern
                     THEN 'Must match the pattern ' || f.pattern END
        END;

        IF message IS NULL AND f.field_type IN ('integer', 'decimal') THEN
            n := v::numeric;
            message := CASE WHEN n < f.min_value THEN format('Must be at least %s.', f.min_value)
                            WHEN n > f.max_value THEN format('Must be at most %s.', f.max_value) END;
        END IF;

        IF message IS NOT NULL THEN
            RETURN NEXT;
        END IF;
    END LOOP;
END $$;


