import pytest
from app.db import as_jsonb, db_error, execute, fetch_all, fetch_one, fetch_value
pytestmark = pytest.mark.django_db

def test_fetch_helpers():
    assert fetch_all("SELECT 1 AS a, 'x' AS b UNION ALL SELECT 2, 'y' ORDER BY a") == [{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]
    assert fetch_one('SELECT 1 AS a WHERE false') is None
    assert fetch_value('SELECT 42') == 42
    assert fetch_value('SELECT 1 WHERE false') is None

def test_json_columns_are_decoded():
    row = fetch_one("SELECT %s::jsonb AS doc, '[1]'::json AS arr", [as_jsonb({'a': [1, True, None]})])
    assert row == {'doc': {'a': [1, True, None]}, 'arr': [1]}

def test_statements_without_result_rows():
    assert fetch_all('CREATE TEMP TABLE t (x int)') == []
    assert execute('INSERT INTO t VALUES (1), (2)') == 2

def test_db_error_without_database_cause():
    assert db_error(Exception()) == (None, None)
