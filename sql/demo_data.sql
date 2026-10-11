



SET LOCAL confighub.allow_backdate = 'on';
SELECT setseed(0.42);

INSERT INTO product (code, name, description) VALUES
    ('pricing-feed',   'Pricing Feed',   'Daily price files delivered to retail clients'' storage, consumed by their shop systems.'),
    ('sales-forecast', 'Sales Forecast', 'Weekly demand forecast per client, used for purchasing and staffing decisions.'),
    ('inventory-sync', 'Inventory Sync', 'Stock level synchronisation between client warehouses and the central inventory tables.');

INSERT INTO client (name) VALUES
    ('Northwind Retail'), ('Contoso Foods'), ('Fabrikam Pharma'), ('Tailspin Toys'),
    ('Litware Electronics'), ('Adventure Works'), ('Wide World Importers'), ('Proseware Fashion');

INSERT INTO membership (user_id, product_id, role)
SELECT u.id, p.id, m.role
FROM (VALUES
    ('anna',   'pricing-feed',   'manager'),
    ('ewa',    'pricing-feed',   'editor'),
    ('jan',    'pricing-feed',   'editor'),
    ('tomasz', 'sales-forecast', 'manager'),
    ('ewa',    'sales-forecast', 'editor'),
    ('piotr',  'inventory-sync', 'manager'),
    ('tomasz', 'inventory-sync', 'editor'),
    ('jan',    'inventory-sync', 'editor')
) AS m (username, product_code, role)
JOIN app_user u ON u.username = m.username
JOIN product p  ON p.code = m.product_code;

INSERT INTO schema_field (product_id, position, key, label, field_type, required, min_value, max_value, choices, pattern, help_text)
SELECT p.id, f.position, f.key, f.label, f.field_type, f.required, f.min_value, f.max_value, f.choices, f.pattern, f.help_text
FROM (VALUES
    ('pricing-feed',   0, 'source_path',        'Source path',              'text',    true,  NULL::numeric, NULL::numeric, NULL::text[], '^/mnt/[a-z0-9_/-]+$', 'Folder in the data lake, e.g. /mnt/prices/northwind'),
    ('pricing-feed',   1, 'currency',           'Currency',                 'choice',  true,  NULL, NULL, ARRAY['EUR', 'USD', 'PLN', 'GBP'], NULL, ''),
    ('pricing-feed',   2, 'refresh_hours',      'Refresh every (hours)',    'integer', true,  1, 168, NULL, NULL, ''),
    ('pricing-feed',   3, 'max_discount_pct',   'Max discount (%)',         'decimal', true,  0, 90, NULL, NULL, ''),
    ('pricing-feed',   4, 'include_promotions', 'Include promotions',       'boolean', false, NULL, NULL, NULL, NULL, ''),
    ('pricing-feed',   5, 'go_live_date',       'Go-live date',             'date',    false, NULL, NULL, NULL, NULL, ''),
    ('sales-forecast', 0, 'model_type',         'Model',                    'choice',  true,  NULL, NULL, ARRAY['prophet', 'arima', 'xgboost'], NULL, ''),
    ('sales-forecast', 1, 'horizon_weeks',      'Forecast horizon (weeks)', 'integer', true,  1, 52, NULL, NULL, ''),
    ('sales-forecast', 2, 'confidence_level',   'Confidence level',         'decimal', true,  0.5, 0.99, NULL, NULL, ''),
    ('sales-forecast', 3, 'exclude_holidays',   'Exclude public holidays',  'boolean', false, NULL, NULL, NULL, NULL, ''),
    ('sales-forecast', 4, 'contact_email',      'Client contact email',     'text',    true,  NULL, NULL, NULL, '^[^@\s]+@[^@\s]+\.[a-z]+$', ''),
    ('inventory-sync', 0, 'warehouse_code',     'Warehouse code',           'text',    true,  NULL, NULL, NULL, '^[A-Z]{3}-\d{2}$', 'Format: ABC-01'),
    ('inventory-sync', 1, 'region',             'Region',                   'choice',  true,  NULL, NULL, ARRAY['EU', 'US', 'APAC'], NULL, ''),
    ('inventory-sync', 2, 'sync_interval_min',  'Sync interval (minutes)',  'integer', true,  5, 1440, NULL, NULL, ''),
    ('inventory-sync', 3, 'safety_stock_units', 'Safety stock (units)',     'integer', true,  0, 100000, NULL, NULL, ''),
    ('inventory-sync', 4, 'notify_on_failure',  'Notify on failure',        'boolean', false, NULL, NULL, NULL, NULL, '')
) AS f (product_code, position, key, label, field_type, required, min_value, max_value, choices, pattern, help_text)
JOIN product p ON p.code = f.product_code;

CREATE FUNCTION pg_temp.demo_value(f schema_field, client_name text) RETURNS jsonb
LANGUAGE sql AS $$
    SELECT CASE f.field_type
        WHEN 'integer' THEN to_jsonb(f.min_value::int + floor(random() * (f.max_value - f.min_value + 1))::int)
        WHEN 'decimal' THEN to_jsonb(round(f.min_value + random()::numeric * (f.max_value - f.min_value), 2))
        WHEN 'boolean' THEN to_jsonb(random() < 0.5)
        WHEN 'date'    THEN to_jsonb(to_char(current_date + floor(random() * 150)::int - 60, 'YYYY-MM-DD'))
        WHEN 'choice'  THEN to_jsonb(f.choices[1 + floor(random() * cardinality(f.choices))::int])
        ELSE to_jsonb(CASE f.key
            WHEN 'source_path'    THEN '/mnt/prices/' || lower(split_part(client_name, ' ', 1))
            WHEN 'contact_email'  THEN 'data@' || lower(split_part(client_name, ' ', 1)) || '.example.com'
            WHEN 'warehouse_code' THEN (ARRAY['WAW', 'KRK', 'BER', 'AMS', 'NYC'])[1 + floor(random() * 5)::int]
                                       || '-0' || (1 + floor(random() * 9)::int)
        END)
    END;
$$;

DO $$
DECLARE
    p        record;
    cl       record;
    cfg_id   bigint;
    v_data   jsonb;
    v_prev   jsonb;
    ts       timestamptz;
    comments text[] := ARRAY['Client asked for a higher refresh rate', 'Align with the new contract',
                             'Fix value that caused a failed run', 'Quarterly review',
                             'Adjust after client feedback', 'Prepare for peak season'];
BEGIN
    FOR p IN SELECT * FROM product ORDER BY id LOOP
        FOR cl IN SELECT * FROM client ORDER BY random() LIMIT 6 LOOP
            INSERT INTO configuration (product_id, client_id, status)
            VALUES (p.id, cl.id, CASE WHEN random() < 0.15 THEN 'disabled' ELSE 'active' END)
            RETURNING id INTO cfg_id;

            ts := now() - make_interval(days => 20 + floor(random() * 20)::int);
            v_data := (SELECT jsonb_object_agg(f.key, pg_temp.demo_value(f, cl.name)) FROM schema_field f WHERE f.product_id = p.id);
            INSERT INTO config_version (configuration_id, data, author_id, comment, created_at)
            VALUES (cfg_id, v_data, (SELECT user_id FROM membership WHERE product_id = p.id ORDER BY random() LIMIT 1),
                    'Initial configuration', ts);

            FOR i IN 2 .. 1 + floor(random() * 5)::int LOOP
                v_prev := v_data;

                SELECT v_data || jsonb_object_agg(f.key, pg_temp.demo_value(f, cl.name)) INTO v_data
                FROM (SELECT * FROM schema_field WHERE product_id = p.id ORDER BY random() LIMIT 1 + floor(random() * 2)::int) f;
                CONTINUE WHEN v_data = v_prev;
                ts := least(ts + make_interval(hours => 6 + floor(random() * 144)::int), now());
                INSERT INTO config_version (configuration_id, data, author_id, comment, created_at)
                VALUES (cfg_id, v_data,
                        (SELECT user_id FROM membership WHERE product_id = p.id ORDER BY random() LIMIT 1),
                        comments[1 + floor(random() * cardinality(comments))::int],
                        ts);
            END LOOP;
        END LOOP;
    END LOOP;
END $$;
