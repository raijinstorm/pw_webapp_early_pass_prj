-- Validation and versioning.
--
-- How a change is saved: INSERT a row into config_version. Triggers then
--   1. lock the configuration, validate the data against the product schema,
--      refuse a version that changes nothing, and assign the next version number;
--   2. copy the data into configuration (the "current state" cache).
-- Nobody can edit configuration.data directly, and versions can never be updated or deleted.


-- Every problem with p_data for this product's schema, one row per key.
-- field_key is NULL for problems that concern the whole object.
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

    -- Keys the schema does not know (e.g. a field that was deleted).
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
        -- CASE is evaluated in order, so the casts below only run on values of the right JSON type.
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


CREATE FUNCTION config_version_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    cfg    configuration;
    errors jsonb;
BEGIN
    -- Lock the configuration so two simultaneous saves get consecutive numbers.
    SELECT * INTO cfg FROM configuration WHERE id = NEW.configuration_id FOR UPDATE;

    SELECT jsonb_object_agg(coalesce(field_key, '__all__'), message) INTO errors
    FROM config_errors(cfg.product_id, NEW.data);
    IF errors IS NOT NULL THEN
        RAISE EXCEPTION 'Configuration data does not match the product schema.'
            USING ERRCODE = 'check_violation', CONSTRAINT = 'config_data_matches_schema', DETAIL = errors::text;
    END IF;

    IF cfg.version > 0 AND NEW.data = cfg.data THEN
        RAISE EXCEPTION 'Nothing changed: there is no new version to save.'
            USING ERRCODE = 'check_violation', CONSTRAINT = 'config_version_has_changes';
    END IF;

    NEW.number := cfg.version + 1;
    -- Audit timestamps come from the database clock. Only the demo-data script may backdate them.
    IF current_setting('confighub.allow_backdate', true) IS DISTINCT FROM 'on' THEN
        NEW.created_at := now();
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER config_version_before_insert
    BEFORE INSERT ON config_version
    FOR EACH ROW EXECUTE FUNCTION config_version_before_insert();


CREATE FUNCTION config_version_after_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE configuration
    SET data = NEW.data, version = NEW.number, updated_by_id = NEW.author_id, updated_at = NEW.created_at
    WHERE id = NEW.configuration_id;
    RETURN NULL;
END $$;

CREATE TRIGGER config_version_after_insert
    AFTER INSERT ON config_version
    FOR EACH ROW EXECUTE FUNCTION config_version_after_insert();


-- History is append-only.
CREATE FUNCTION config_version_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Configuration versions are immutable and cannot be changed or deleted.'
        USING ERRCODE = 'restrict_violation';
END $$;

CREATE TRIGGER config_version_immutable
    BEFORE UPDATE OR DELETE ON config_version
    FOR EACH ROW EXECUTE FUNCTION config_version_immutable();


-- configuration.data/version may only be written by the config_version trigger (trigger depth 2).
-- A new configuration starts empty at version 0.
CREATE FUNCTION configuration_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' AND (NEW.data <> '{}' OR NEW.version <> 0) THEN
        RAISE EXCEPTION 'A new configuration starts empty; add its values by inserting a config_version.'
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF TG_OP = 'UPDATE' AND pg_trigger_depth() < 2
       AND (NEW.data IS DISTINCT FROM OLD.data OR NEW.version IS DISTINCT FROM OLD.version) THEN
        RAISE EXCEPTION 'Configuration data can only change by inserting a config_version.'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER configuration_guard
    BEFORE INSERT OR UPDATE ON configuration
    FOR EACH ROW EXECUTE FUNCTION configuration_guard();


-- A field's key and product never change: stored data refers to them.
CREATE FUNCTION schema_field_key_locked() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.key <> OLD.key OR NEW.product_id <> OLD.product_id THEN
        RAISE EXCEPTION 'The key and product of a schema field cannot be changed.'
            USING ERRCODE = 'check_violation', CONSTRAINT = 'schema_field_key_locked';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER schema_field_key_locked
    BEFORE UPDATE ON schema_field
    FOR EACH ROW EXECUTE FUNCTION schema_field_key_locked();


-- Create a configuration together with its first version, in one call.
CREATE FUNCTION create_configuration(p_product_id bigint, p_client_id bigint, p_data jsonb, p_author_id bigint, p_comment text)
RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE
    new_id bigint;
BEGIN
    INSERT INTO configuration (product_id, client_id) VALUES (p_product_id, p_client_id) RETURNING id INTO new_id;
    INSERT INTO config_version (configuration_id, data, author_id, comment) VALUES (new_id, p_data, p_author_id, p_comment);
    RETURN new_id;
END $$;

-- Save an old version's data as a new version. Returns the new version number.
CREATE FUNCTION restore_version(p_version_id bigint, p_author_id bigint) RETURNS integer
LANGUAGE sql AS $$
    INSERT INTO config_version (configuration_id, data, author_id, comment)
    SELECT configuration_id, data, p_author_id, format('Restored version %s', number)
    FROM config_version WHERE id = p_version_id
    RETURNING number;
$$;
