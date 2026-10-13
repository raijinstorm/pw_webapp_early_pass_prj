import pytest
from django.db import IntegrityError, transaction
from app.db import db_error, execute, fetch_value
pytestmark = pytest.mark.django_db

def violated(sql, params=None):
    with pytest.raises(IntegrityError) as exc, transaction.atomic():
        execute(sql, params)
    return db_error(exc.value)[0]
FIELD = "INSERT INTO schema_field (product_id, key, label, field_type, required, min_value, max_value, choices, pattern) VALUES (%s, %s, 'L', %s, %s, %s, %s, %s, %s)"

@pytest.mark.parametrize('key, field_type, required, min_v, max_v, choices, pattern, constraint', [('Bad', 'text', True, None, None, None, None, 'schema_field_key_format'), ('k', 'money', True, None, None, None, None, 'schema_field_type_valid'), ('k', 'text', True, 1, None, None, None, 'schema_field_range_only_numeric'), ('k', 'integer', True, 5, 1, None, None, 'schema_field_min_le_max'), ('k', 'choice', True, None, None, None, None, 'schema_field_choices_only_choice'), ('k', 'text', True, None, None, ['a', 'b'], None, 'schema_field_choices_only_choice'), ('k', 'choice', True, None, None, ['only'], None, 'schema_field_choices_at_least_two'), ('k', 'integer', True, None, None, None, 'x', 'schema_field_pattern_only_text'), ('k', 'text', True, None, None, None, '(', 'schema_field_pattern_valid'), ('k', 'boolean', True, None, None, None, None, 'schema_field_boolean_optional')])
def test_schema_field_rules(product, key, field_type, required, min_v, max_v, choices, pattern, constraint):
    assert violated(FIELD, [product.id, key, field_type, required, min_v, max_v, choices, pattern]) == constraint

def test_valid_schema_field_is_accepted(product):
    execute(FIELD, [product.id, 'region', 'choice', True, None, None, ['EU', 'US'], None])
    execute(FIELD, [product.id, 'code', 'text', True, None, None, None, '^[A-Z]{3}$'])

def test_schema_field_key_unique_per_product(product, other_product):
    assert violated(FIELD, [product.id, 'hours', 'integer', True, None, None, None, None]) == 'schema_field_key_unique'
    execute(FIELD, [other_product.id, 'hours', 'integer', True, None, None, None, None])

def test_schema_field_key_cannot_change(product):
    assert violated("UPDATE schema_field SET key = 'renamed' WHERE key = 'hours'") == 'schema_field_key_locked'
    execute("UPDATE schema_field SET label = 'Renamed' WHERE key = 'hours'")

@pytest.mark.parametrize('sql, constraint', [("INSERT INTO product (code, name) VALUES ('Bad Code', 'X')", 'product_code_format'), ("INSERT INTO product (code, name) VALUES ('ok', '  ')", 'product_name_not_blank'), ("INSERT INTO product (code, name) VALUES ('pricing', 'Other')", 'product_code_unique'), ("INSERT INTO client (name) VALUES ('')", 'client_name_not_blank')])
def test_reference_data_rules(product, sql, constraint):
    assert violated(sql) == constraint

def test_membership_rules(product, editor):
    sql = 'INSERT INTO membership (user_id, product_id, role) VALUES (%s, %s, %s)'
    assert violated(sql, [editor.id, product.id, 'editor']) == 'membership_unique'
    assert violated(sql, [editor.id, product.id + 1000, 'owner']) == 'membership_role_valid'

def test_configuration_status_and_uniqueness(configuration, product, customer):
    assert violated("UPDATE configuration SET status = 'archived' WHERE id = %s", [configuration]) == 'configuration_status_valid'
    assert violated('INSERT INTO configuration (product_id, client_id) VALUES (%s, %s)', [product.id, customer.id]) == 'configuration_product_client_unique'

def test_regex_and_date_helpers(db):
    assert fetch_value("SELECT is_valid_regex('^a+$')") is True
    assert fetch_value("SELECT is_valid_regex('(')") is False
    assert fetch_value("SELECT is_valid_date('2026-02-28')") is True
    assert fetch_value("SELECT is_valid_date('2026-02-30')") is False
    assert fetch_value("SELECT is_valid_date('28.02.2026')") is False
