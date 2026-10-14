"""All SQL used by the pages. Each function is one query; rules and logic live in the database (sql/)."""

from django.conf import settings

from .db import as_jsonb, execute, fetch_all, fetch_one, fetch_value

# ---------- Access ----------


def user_role(user_id, product_id):
    """'admin', 'manager', 'editor' or None."""
    return fetch_value("SELECT user_role(%s, %s)", [user_id, product_id])


def product_by_id(product_id):
    return fetch_one("SELECT * FROM product WHERE id = %s", [product_id])


def product_by_code(code):
    return fetch_one("SELECT * FROM product WHERE code = %s", [code])


def visible_products(user_id):
    """Products the user can see, with their role and number of configurations (dashboard cards)."""
    return fetch_all(
        """
        SELECT p.id, p.code, p.name, p.description,
               user_role(%(user)s, p.id) AS role,
               (SELECT count(*) FROM configuration c WHERE c.product_id = p.id) AS config_count
        FROM product p
        WHERE p.id IN (SELECT product_id FROM visible_product_ids(%(user)s))
        ORDER BY p.name
        """,
        {"user": user_id},
    )


# ---------- Table 1: configurations ----------


def configurations(user_id, product=None, client=None, status=None, search=None):
    """Configurations visible to the user. Every filter is optional (None = no filter)."""
    return fetch_all(
        """
        SELECT * FROM configuration_overview
        WHERE product_id IN (SELECT product_id FROM visible_product_ids(%(user)s))
          AND (%(product)s::text IS NULL OR product_code = %(product)s)
          AND (%(client)s::bigint IS NULL OR client_id = %(client)s)
          AND (%(status)s::text IS NULL OR status = %(status)s)
          AND (%(search)s::text IS NULL OR client_name ILIKE '%%' || %(search)s || '%%')
        ORDER BY product_name, client_name
        """,
        {"user": user_id, "product": product, "client": client, "status": status, "search": search},
    )


def configuration(config_id):
    return fetch_one("SELECT * FROM configuration_overview WHERE id = %s", [config_id])


# ---------- Table 2: history ----------


def versions(user_id, product=None, author=None, date_from=None, date_to=None, limit=None):
    """Change history visible to the user, newest first. Every filter is optional; dates are local days."""
    return fetch_all(
        """
        SELECT * FROM version_overview
        WHERE product_id IN (SELECT product_id FROM visible_product_ids(%(user)s))
          AND (%(product)s::text IS NULL OR product_code = %(product)s)
          AND (%(author)s::text IS NULL OR author = %(author)s)
          AND (%(date_from)s::date IS NULL OR (created_at AT TIME ZONE %(tz)s)::date >= %(date_from)s)
          AND (%(date_to)s::date IS NULL OR (created_at AT TIME ZONE %(tz)s)::date <= %(date_to)s)
        ORDER BY created_at DESC, id DESC
        LIMIT %(limit)s
        """,
        {
            "user": user_id, "product": product, "author": author,
            "date_from": date_from, "date_to": date_to, "tz": settings.TIME_ZONE, "limit": limit,
        },
    )


def history_authors(user_id):
    return fetch_all(
        """
        SELECT DISTINCT author FROM version_overview
        WHERE author IS NOT NULL
          AND product_id IN (SELECT product_id FROM visible_product_ids(%s))
        ORDER BY author
        """,
        [user_id],
    )


def configuration_versions(config_id):
    return fetch_all("SELECT * FROM version_overview WHERE configuration_id = %s ORDER BY number DESC", [config_id])


def version(version_id):
    return fetch_one("SELECT * FROM version_overview WHERE id = %s", [version_id])


def version_changes(version_id):
    return fetch_all("SELECT key, old_value AS old, new_value AS new FROM version_changes(%s)", [version_id])


# ---------- Writing configurations (validation and versioning happen in triggers) ----------


def create_configuration(product_id, client_id, data, author_id, comment):
    return fetch_value(
        "SELECT create_configuration(%s, %s, %s::jsonb, %s, %s)",
        [product_id, client_id, as_jsonb(data), author_id, comment],
    )


def save_version(config_id, data, author_id, comment):
    """Insert a new version; returns its number."""
    return fetch_value(
        """
        INSERT INTO config_version (configuration_id, data, author_id, comment)
        VALUES (%s, %s::jsonb, %s, %s)
        RETURNING number
        """,
        [config_id, as_jsonb(data), author_id, comment],
    )


def restore_version(version_id, author_id):
    return fetch_value("SELECT restore_version(%s, %s)", [version_id, author_id])


def toggle_status(config_id):
    return fetch_value(
        """
        UPDATE configuration
        SET status = CASE status WHEN 'active' THEN 'disabled' ELSE 'active' END, updated_at = now()
        WHERE id = %s
        RETURNING status
        """,
        [config_id],
    )


# ---------- Reference data ----------


def clients():
    return fetch_all("SELECT id, name FROM client ORDER BY name")


def clients_without_configuration(product_id):
    return fetch_all(
        """
        SELECT id, name FROM client
        WHERE id NOT IN (SELECT client_id FROM configuration WHERE product_id = %s)
        ORDER BY name
        """,
        [product_id],
    )


# ---------- Schema fields ----------

FIELD_COLUMNS = ["label", "field_type", "required", "min_value", "max_value", "choices", "pattern", "help_text", "position"]


def schema_fields(product_id):
    return fetch_all("SELECT * FROM schema_field WHERE product_id = %s ORDER BY position, key", [product_id])


def schema_field(product_id, field_id):
    return fetch_one("SELECT * FROM schema_field WHERE product_id = %s AND id = %s", [product_id, field_id])


def insert_schema_field(product_id, values):
    return fetch_value(
        """
        INSERT INTO schema_field (product_id, key, label, field_type, required, min_value, max_value,
                                  choices, pattern, help_text, position)
        VALUES (%(product_id)s, %(key)s, %(label)s, %(field_type)s, %(required)s, %(min_value)s, %(max_value)s,
                %(choices)s, %(pattern)s, %(help_text)s, %(position)s)
        RETURNING id
        """,
        {"product_id": product_id, **values},
    )


def update_schema_field(field_id, values):
    return execute(
        """
        UPDATE schema_field
        SET label = %(label)s, field_type = %(field_type)s, required = %(required)s,
            min_value = %(min_value)s, max_value = %(max_value)s, choices = %(choices)s,
            pattern = %(pattern)s, help_text = %(help_text)s, position = %(position)s
        WHERE id = %(id)s
        """,
        {"id": field_id, **{k: values[k] for k in FIELD_COLUMNS}},
    )


def delete_schema_field(field_id):
    execute("DELETE FROM schema_field WHERE id = %s", [field_id])


# ---------- Members ----------


def members(product_id):
    return fetch_all(
        """
        SELECT m.id, m.user_id, m.role, u.username,
               nullif(btrim(u.first_name || ' ' || u.last_name), '') AS full_name
        FROM membership m JOIN app_user u ON u.id = m.user_id
        WHERE m.product_id = %s
        ORDER BY m.role, u.username
        """,
        [product_id],
    )


def membership(membership_id):
    return fetch_one("SELECT * FROM membership WHERE id = %s", [membership_id])


def active_user_id(username):
    return fetch_value("SELECT id FROM app_user WHERE username = %s AND is_active", [username])


def add_member(product_id, user_id, role):
    return execute("INSERT INTO membership (user_id, product_id, role) VALUES (%s, %s, %s)", [user_id, product_id, role])


def remove_member(membership_id):
    execute("DELETE FROM membership WHERE id = %s", [membership_id])
