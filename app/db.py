"""Tiny helpers for running parameterized SQL and reading database errors."""

import json

from django.db import connection


# PostgreSQL type OIDs of json and jsonb. Django configures psycopg to return these as text
# (its JSONField decodes them itself), so raw queries decode them here.
JSON_TYPES = {114, 3802}


def fetch_all(sql, params=None):
    """Run a query and return the rows as a list of dicts."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        if cursor.description is None:
            return []
        columns = [col.name for col in cursor.description]
        json_columns = {col.name for col in cursor.description if col.type_code in JSON_TYPES}
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for row in rows:
        for name in json_columns:
            if isinstance(row[name], str):
                row[name] = json.loads(row[name])
    return rows


def fetch_one(sql, params=None):
    """Run a query and return the first row as a dict, or None."""
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def fetch_value(sql, params=None):
    """Run a query and return the first column of the first row, or None."""
    row = fetch_one(sql, params)
    return next(iter(row.values())) if row else None


def execute(sql, params=None):
    """Run a statement and return the number of affected rows."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount


def as_jsonb(value):
    """Pass a Python dict to a jsonb parameter."""
    return json.dumps(value)


def db_error(error):
    """(constraint_name, detail) of a database error raised by a constraint or trigger."""
    diag = getattr(error.__cause__, "diag", None)
    if diag is None:
        return None, None
    return diag.constraint_name, diag.message_detail
