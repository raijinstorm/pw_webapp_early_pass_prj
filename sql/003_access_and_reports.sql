-- Access rules and read models used by the pages.


-- 'admin', 'manager', 'editor', or NULL when the user has no access to the product.
CREATE FUNCTION user_role(p_user_id bigint, p_product_id bigint) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT CASE
        WHEN u.is_superuser THEN 'admin'
        ELSE (SELECT m.role FROM membership m WHERE m.user_id = u.id AND m.product_id = p_product_id)
    END
    FROM app_user u
    WHERE u.id = p_user_id AND u.is_active;
$$;

-- Products the user may see: all for admins, otherwise the ones they are a member of.
CREATE FUNCTION visible_product_ids(p_user_id bigint) RETURNS TABLE (product_id bigint)
LANGUAGE sql STABLE AS $$
    SELECT p.id FROM product p
    WHERE EXISTS (SELECT 1 FROM app_user u WHERE u.id = p_user_id AND u.is_superuser AND u.is_active)
    UNION
    SELECT m.product_id FROM membership m
    JOIN app_user u ON u.id = m.user_id AND u.is_active
    WHERE m.user_id = p_user_id;
$$;


-- Table 1: configurations with readable names.
CREATE VIEW configuration_overview AS
SELECT c.id,
       c.product_id,
       p.code     AS product_code,
       p.name     AS product_name,
       c.client_id,
       cl.name    AS client_name,
       c.status,
       c.version,
       c.data,
       c.updated_at,
       u.username AS updated_by
FROM configuration c
JOIN product p  ON p.id = c.product_id
JOIN client cl  ON cl.id = c.client_id
LEFT JOIN app_user u ON u.id = c.updated_by_id;

-- Table 2: change history with readable names.
CREATE VIEW version_overview AS
SELECT v.id,
       v.configuration_id,
       v.number,
       v.number = c.version AS is_current,
       v.data,
       v.comment,
       v.created_at,
       v.author_id,
       u.username AS author,
       c.product_id,
       p.code     AS product_code,
       p.name     AS product_name,
       cl.name    AS client_name
FROM config_version v
JOIN configuration c ON c.id = v.configuration_id
JOIN product p       ON p.id = c.product_id
JOIN client cl       ON cl.id = c.client_id
LEFT JOIN app_user u ON u.id = v.author_id;


-- What one version changed compared with the version before it (all keys for version 1),
-- in schema order. Keys no longer in the schema come last.
CREATE FUNCTION version_changes(p_version_id bigint)
RETURNS TABLE (key text, old_value jsonb, new_value jsonb)
LANGUAGE sql STABLE AS $$
    WITH cur AS (
        SELECT v.configuration_id, v.number, v.data, c.product_id
        FROM config_version v JOIN configuration c ON c.id = v.configuration_id
        WHERE v.id = p_version_id
    ),
    prev AS (
        SELECT coalesce(
            (SELECT v.data FROM config_version v, cur
             WHERE v.configuration_id = cur.configuration_id AND v.number = cur.number - 1),
            '{}'::jsonb) AS data
    ),
    keys AS (
        SELECT jsonb_object_keys(cur.data) AS key FROM cur
        UNION
        SELECT jsonb_object_keys(prev.data) FROM prev
    )
    -- A JSON null counts as "no value", the same as a missing key.
    SELECT k.key, nullif(prev.data -> k.key, 'null'), nullif(cur.data -> k.key, 'null')
    FROM keys k
    CROSS JOIN cur
    CROSS JOIN prev
    LEFT JOIN schema_field f ON f.product_id = cur.product_id AND f.key = k.key
    WHERE nullif(prev.data -> k.key, 'null') IS DISTINCT FROM nullif(cur.data -> k.key, 'null')
    ORDER BY f.position NULLS LAST, k.key;
$$;
