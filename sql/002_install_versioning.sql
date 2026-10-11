ALTER TABLE product ALTER COLUMN description SET DEFAULT '';
ALTER TABLE product ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE schema_field ALTER COLUMN field_type SET DEFAULT 'text';
ALTER TABLE schema_field ALTER COLUMN required SET DEFAULT true;
ALTER TABLE schema_field ALTER COLUMN help_text SET DEFAULT '';
ALTER TABLE schema_field ALTER COLUMN position SET DEFAULT 0;
ALTER TABLE membership ALTER COLUMN role SET DEFAULT 'editor';
ALTER TABLE config_version ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE configuration ALTER COLUMN status SET DEFAULT 'active';
ALTER TABLE configuration ALTER COLUMN data SET DEFAULT '{}';
ALTER TABLE configuration ALTER COLUMN version SET DEFAULT 0;
ALTER TABLE configuration ALTER COLUMN updated_at SET DEFAULT now();
INSERT INTO config_version (configuration_id, number, data, comment, author_id, created_at)
SELECT c.id, greatest(c.version, 1), c.data, 'Initial snapshot', c.updated_by_id, c.updated_at
FROM configuration c WHERE NOT EXISTS (SELECT 1 FROM config_version v WHERE v.configuration_id = c.id);
UPDATE configuration c SET version = v.number FROM (SELECT configuration_id, max(number) AS number FROM config_version GROUP BY configuration_id) v WHERE c.id = v.configuration_id;
CREATE FUNCTION config_version_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    cfg    configuration;
    errors jsonb;
BEGIN

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

CREATE FUNCTION config_version_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Configuration versions are immutable and cannot be changed or deleted.'
        USING ERRCODE = 'restrict_violation';
END $$;

CREATE TRIGGER config_version_immutable
    BEFORE UPDATE OR DELETE ON config_version
    FOR EACH ROW EXECUTE FUNCTION config_version_immutable();


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

CREATE FUNCTION restore_version(p_version_id bigint, p_author_id bigint) RETURNS integer
LANGUAGE sql AS $$
    INSERT INTO config_version (configuration_id, data, author_id, comment)
    SELECT configuration_id, data, p_author_id, format('Restored version %s', number)
    FROM config_version WHERE id = p_version_id
    RETURNING number;
$$;
