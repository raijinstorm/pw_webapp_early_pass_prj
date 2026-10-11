from django.conf import settings
from .db import as_jsonb, execute, fetch_all, fetch_one, fetch_value

def user_role(user_id, product_id):
    return fetch_value('SELECT user_role(%s, %s)', [user_id, product_id])

def product_by_id(product_id):
    return fetch_one('SELECT * FROM product WHERE id = %s', [product_id])

def product_by_code(code):
    return fetch_one('SELECT * FROM product WHERE code = %s', [code])

def visible_products(user_id):
    return fetch_all('\n        SELECT p.id, p.code, p.name, p.description,\n               user_role(%(user)s, p.id) AS role,\n               (SELECT count(*) FROM configuration c WHERE c.product_id = p.id) AS config_count\n        FROM product p\n        WHERE p.id IN (SELECT product_id FROM visible_product_ids(%(user)s))\n        ORDER BY p.name\n        ', {'user': user_id})

def configurations(user_id, product=None, client=None, status=None, search=None):
    return fetch_all("\n        SELECT * FROM configuration_overview\n        WHERE product_id IN (SELECT product_id FROM visible_product_ids(%(user)s))\n          AND (%(product)s::text IS NULL OR product_code = %(product)s)\n          AND (%(client)s::bigint IS NULL OR client_id = %(client)s)\n          AND (%(status)s::text IS NULL OR status = %(status)s)\n          AND (%(search)s::text IS NULL OR client_name ILIKE '%%' || %(search)s || '%%')\n        ORDER BY product_name, client_name\n        ", {'user': user_id, 'product': product, 'client': client, 'status': status, 'search': search})

def configuration(config_id):
    return fetch_one('SELECT * FROM configuration_overview WHERE id = %s', [config_id])

def versions(user_id, product=None, author=None, date_from=None, date_to=None, limit=None):
    return fetch_all('\n        SELECT * FROM version_overview\n        WHERE product_id IN (SELECT product_id FROM visible_product_ids(%(user)s))\n          AND (%(product)s::text IS NULL OR product_code = %(product)s)\n          AND (%(author)s::text IS NULL OR author = %(author)s)\n          AND (%(date_from)s::date IS NULL OR (created_at AT TIME ZONE %(tz)s)::date >= %(date_from)s)\n          AND (%(date_to)s::date IS NULL OR (created_at AT TIME ZONE %(tz)s)::date <= %(date_to)s)\n        ORDER BY created_at DESC, id DESC\n        LIMIT %(limit)s\n        ', {'user': user_id, 'product': product, 'author': author, 'date_from': date_from, 'date_to': date_to, 'tz': 'UTC', 'limit': limit})

def history_authors(user_id):
    return fetch_all('\n        SELECT DISTINCT author FROM version_overview\n        WHERE author IS NOT NULL\n          AND product_id IN (SELECT product_id FROM visible_product_ids(%s))\n        ORDER BY author\n        ', [user_id])

def configuration_versions(config_id):
    return fetch_all('SELECT * FROM version_overview WHERE configuration_id = %s ORDER BY number DESC', [config_id])

def version(version_id):
    return fetch_one('SELECT * FROM version_overview WHERE id = %s', [version_id])

def version_changes(version_id):
    return fetch_all('SELECT key, old_value AS old, new_value AS new FROM version_changes(%s)', [version_id])

def create_configuration(product_id, client_id, data, author_id, comment):
    return fetch_value('SELECT create_configuration(%s, %s, %s::jsonb, %s, %s)', [product_id, client_id, as_jsonb(data), author_id, comment])

def save_version(config_id, data, author_id, comment):
    return fetch_value('\n        INSERT INTO config_version (configuration_id, data, author_id, comment)\n        VALUES (%s, %s::jsonb, %s, %s)\n        RETURNING number\n        ', [config_id, as_jsonb(data), author_id, comment])

def restore_version(version_id, author_id):
    return fetch_value('SELECT restore_version(%s, %s)', [version_id, author_id])

def toggle_status(config_id):
    return fetch_value("\n        UPDATE configuration\n        SET status = CASE status WHEN 'active' THEN 'disabled' ELSE 'active' END, updated_at = now()\n        WHERE id = %s\n        RETURNING status\n        ", [config_id])

def clients():
    return fetch_all('SELECT id, name FROM client ORDER BY name')

def clients_without_configuration(product_id):
    return fetch_all('\n        SELECT id, name FROM client\n        WHERE id NOT IN (SELECT client_id FROM configuration WHERE product_id = %s)\n        ORDER BY name\n        ', [product_id])
FIELD_COLUMNS = ['label', 'field_type', 'required', 'min_value', 'max_value', 'choices', 'pattern', 'help_text', 'position']

def schema_fields(product_id):
    return fetch_all('SELECT * FROM schema_field WHERE product_id = %s ORDER BY position, key', [product_id])

def schema_field(product_id, field_id):
    return fetch_one('SELECT * FROM schema_field WHERE product_id = %s AND id = %s', [product_id, field_id])

def insert_schema_field(product_id, values):
    return fetch_value('\n        INSERT INTO schema_field (product_id, key, label, field_type, required, min_value, max_value,\n                                  choices, pattern, help_text, position)\n        VALUES (%(product_id)s, %(key)s, %(label)s, %(field_type)s, %(required)s, %(min_value)s, %(max_value)s,\n                %(choices)s, %(pattern)s, %(help_text)s, %(position)s)\n        RETURNING id\n        ', {'product_id': product_id, **values})

def update_schema_field(field_id, values):
    return execute('\n        UPDATE schema_field\n        SET label = %(label)s, field_type = %(field_type)s, required = %(required)s,\n            min_value = %(min_value)s, max_value = %(max_value)s, choices = %(choices)s,\n            pattern = %(pattern)s, help_text = %(help_text)s, position = %(position)s\n        WHERE id = %(id)s\n        ', {'id': field_id, **{k: values[k] for k in FIELD_COLUMNS}})

def delete_schema_field(field_id):
    execute('DELETE FROM schema_field WHERE id = %s', [field_id])

def members(product_id):
    return fetch_all("\n        SELECT m.id, m.user_id, m.role, u.username,\n               nullif(btrim(u.first_name || ' ' || u.last_name), '') AS full_name\n        FROM membership m JOIN app_user u ON u.id = m.user_id\n        WHERE m.product_id = %s\n        ORDER BY m.role, u.username\n        ", [product_id])

def membership(membership_id):
    return fetch_one('SELECT * FROM membership WHERE id = %s', [membership_id])

def active_user_id(username):
    return fetch_value('SELECT id FROM app_user WHERE username = %s AND is_active', [username])

def add_member(product_id, user_id, role):
    return execute('INSERT INTO membership (user_id, product_id, role) VALUES (%s, %s, %s)', [user_id, product_id, role])

def remove_member(membership_id):
    execute('DELETE FROM membership WHERE id = %s', [membership_id])
