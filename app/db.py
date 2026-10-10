import json
from django.db import connection
JSON_TYPES = {114, 3802}

def fetch_all(sql, params=None):
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
    rows = fetch_all(sql, params)
    return rows[0] if rows else None

def fetch_value(sql, params=None):
    row = fetch_one(sql, params)
    return next(iter(row.values())) if row else None

def execute(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount

def as_jsonb(value):
    return json.dumps(value)

def db_error(error):
    diag = getattr(error.__cause__, 'diag', None)
    if diag is None:
        return (None, None)
    return (diag.constraint_name, diag.message_detail)
