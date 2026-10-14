"""Forms: input parsing, building the config form from the schema, and mapping database errors to fields."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from app import queries
from app.forms import (
    MEMBER_ERRORS, SCHEMA_FIELD_ERRORS, ConfigForm, HistoryFilterForm, MemberForm, SchemaFieldForm, to_json_value,
)
from tests.conftest import form_data

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "value, expected",
    [(date(2026, 1, 2), "2026-01-02"), (Decimal("12.50"), 12.5), (5, 5), (True, True), ("", None), (None, None)],
)
def test_to_json_value(value, expected):
    assert to_json_value(value) == expected


class TestConfigForm:
    def test_fields_follow_the_schema(self, product_row):
        form = ConfigForm(product=product_row)
        names = [b.name for b in form.value_fields()]
        assert names == ["value__path", "value__hours", "value__discount", "value__promo", "value__start", "value__currency"]
        hours = form.fields["value__hours"].widget.attrs
        assert hours["min"] == 1 and hours["max"] == 24 and hours["required"]
        assert "required" not in form.fields["value__start"].widget.attrs

    def test_create_lists_only_unused_clients(self, product_row, configuration, second_customer):
        form = ConfigForm(product=product_row)
        assert form.fields["client"].choices == [("", "---------"), (second_customer.id, "Globex")]

    def test_parses_values_to_json(self, product_row, customer):
        form = ConfigForm(form_data(client=customer.id), product=product_row)
        assert form.is_valid(), form.errors
        assert form.data_json() == {
            "path": "/mnt/acme", "hours": 6, "discount": 10.5, "promo": True, "start": None, "currency": "EUR",
        }

    def test_type_errors_are_caught_before_the_database(self, product_row, customer):
        form = ConfigForm(form_data(client=customer.id, value__hours="six", value__start="tomorrow"), product=product_row)
        assert not form.is_valid()
        assert {"value__hours", "value__start"} <= set(form.errors)
        assert "is-invalid" in form.fields["value__hours"].widget.attrs["class"]

    def test_edit_prefills_current_values(self, product_row, configuration):
        form = ConfigForm(product=product_row, configuration=queries.configuration(configuration))
        assert form.initial["value__hours"] == 6
        assert "client" not in form.fields

    def test_schema_errors_from_the_database_land_on_fields(self, product_row, configuration, editor):
        form = ConfigForm(form_data(value__hours="99"), product=product_row, configuration=queries.configuration(configuration))
        assert form.is_valid()
        with pytest.raises(IntegrityError) as exc, transaction.atomic():
            queries.save_version(configuration, form.data_json(), editor.id, "x")
        assert form.apply_db_error(exc.value)
        assert form.errors["value__hours"] == ["Must be at most 24."]

    def test_unknown_key_error_becomes_form_error(self, product_row, configuration, editor):
        form = ConfigForm(form_data(), product=product_row, configuration=queries.configuration(configuration))
        form.is_valid()
        with pytest.raises(IntegrityError) as exc, transaction.atomic():
            queries.save_version(configuration, {**form.data_json(), "gone": 1}, editor.id, "x")
        assert form.apply_db_error(exc.value)
        assert form.non_field_errors() == ["gone: Unknown key: not in the product schema."]

    def test_unknown_database_error_is_not_swallowed(self, product_row):
        form = ConfigForm(product=product_row)
        error = Exception()
        assert form.apply_db_error(error) is False


class TestSchemaFieldForm:
    def test_values_for_the_table(self):
        form = SchemaFieldForm({"key": "region", "label": "Region", "field_type": "choice", "choices": " EU, ,US ",
                                "required": "on", "position": 2})
        assert form.is_valid(), form.errors
        values = form.values()
        assert values["choices"] == ["EU", "US"] and values["pattern"] is None and values["required"] is True

    def test_boolean_is_never_required(self):
        form = SchemaFieldForm({"key": "flag", "label": "Flag", "field_type": "boolean", "required": "on", "position": 0})
        assert form.is_valid()
        assert form.values()["required"] is False

    def test_initial_from_row_and_locked_key(self, product):
        row = queries.schema_fields(product.id)[-1]
        initial = SchemaFieldForm.initial_from_row(row)
        assert initial["choices"] == "EUR, PLN" and initial["pattern"] == ""
        assert SchemaFieldForm(initial=initial, editing=True).fields["key"].disabled

    def test_every_schema_constraint_has_a_message(self):
        constraints = {
            "schema_field_key_unique", "schema_field_key_format", "schema_field_label_not_blank",
            "schema_field_range_only_numeric", "schema_field_min_le_max", "schema_field_choices_only_choice",
            "schema_field_choices_at_least_two", "schema_field_pattern_only_text", "schema_field_pattern_valid",
            "schema_field_position_positive",
        }
        assert constraints == set(SCHEMA_FIELD_ERRORS)


class TestMemberForm:
    def test_unknown_user(self):
        assert not MemberForm({"username": "nobody", "role": "editor"}).is_valid()

    def test_valid_user_resolved_by_sql(self, outsider):
        form = MemberForm({"username": f" {outsider.username} ", "role": "manager"})
        assert form.is_valid()
        assert form.user_id == outsider.id
        assert "membership_unique" in MEMBER_ERRORS


class TestFilterForms:
    def test_history_date_range_order(self, editor):
        form = HistoryFilterForm({"date_from": "2026-10-02", "date_to": "2026-10-01"}, user=editor)
        assert not form.is_valid()
        assert "date_to" in form.errors

    def test_choices_come_from_sql(self, editor, configuration):
        form = HistoryFilterForm(user=editor)
        assert form.fields["product"].choices == [("", "All products"), ("pricing", "Pricing")]
        assert form.fields["author"].choices == [("", "Anyone"), ("eddie", "eddie")]
