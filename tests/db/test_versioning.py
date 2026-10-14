"""Schema validation and versioning (sql/002_versioning.sql)."""

import json

import pytest
from django.db import IntegrityError, transaction

from app import queries
from app.db import db_error, execute, fetch_all, fetch_one
from tests.conftest import VALID_DATA

pytestmark = pytest.mark.django_db


def errors(product, data):
    rows = fetch_all("SELECT field_key, message FROM config_errors(%s, %s::jsonb)", [product.id, json.dumps(data)])
    return {r["field_key"]: r["message"] for r in rows}


class TestConfigErrors:
    def test_valid_data_has_no_errors(self, product):
        assert errors(product, VALID_DATA) == {}

    def test_optional_fields_may_be_missing(self, product):
        data = {k: v for k, v in VALID_DATA.items() if k not in ("promo", "start")}
        assert errors(product, data) == {}

    @pytest.mark.parametrize(
        "key, value, message",
        [
            ("path", None, "This field is required."),
            ("path", "", "This field is required."),
            ("path", "C:\\x", "Must match the pattern"),
            ("path", 5, "Must be text."),
            ("path", "/mnt/" + "a" * 500, "At most 500 characters."),
            ("hours", 0, "Must be at least 1."),
            ("hours", 25, "Must be at most 24."),
            ("hours", 2.5, "Must be a whole number."),
            ("hours", "6", "Must be a whole number."),
            ("discount", "ten", "Must be a number."),
            ("discount", 50.01, "Must be at most 50."),
            ("promo", "yes", "Must be true or false."),
            ("start", "2026-02-30", "Must be a date"),
            ("start", 20260101, "Must be a date"),
            ("currency", "USD", "Must be one of: EUR, PLN."),
        ],
    )
    def test_invalid_values(self, product, key, value, message):
        assert errors(product, {**VALID_DATA, key: value})[key].startswith(message)

    def test_unknown_key_and_non_object(self, product):
        assert "Unknown key" in errors(product, {**VALID_DATA, "bogus": 1})["bogus"]
        assert errors(product, [1, 2]) == {None: "Configuration data must be a JSON object."}


class TestVersioning:
    def test_create_configuration_makes_version_one(self, configuration, editor):
        row = queries.configuration(configuration)
        assert row["version"] == 1
        assert row["data"] == VALID_DATA
        assert row["updated_by"] == editor.username

    def test_new_version_updates_current_state(self, configuration, manager):
        number = queries.save_version(configuration, {**VALID_DATA, "hours": 8}, manager.id, "more often")
        row = queries.configuration(configuration)
        assert number == 2 == row["version"]
        assert row["data"]["hours"] == 8 and row["updated_by"] == "manny"

    def test_version_number_from_caller_is_ignored(self, configuration, editor):
        execute(
            "INSERT INTO config_version (configuration_id, number, data, comment, author_id) VALUES (%s, 99, %s::jsonb, 'x', %s)",
            [configuration, json.dumps({**VALID_DATA, "hours": 3}), editor.id],
        )
        assert queries.configuration(configuration)["version"] == 2

    def test_invalid_data_is_rejected_with_details(self, configuration, editor):
        with pytest.raises(IntegrityError) as exc, transaction.atomic():
            queries.save_version(configuration, {**VALID_DATA, "hours": 99, "currency": "JPY"}, editor.id, "bad")
        constraint, detail = db_error(exc.value)
        assert constraint == "config_data_matches_schema"
        assert set(json.loads(detail)) == {"hours", "currency"}
        assert queries.configuration(configuration)["version"] == 1

    def test_identical_data_is_rejected(self, configuration, editor):
        with pytest.raises(IntegrityError) as exc, transaction.atomic():
            queries.save_version(configuration, dict(VALID_DATA), editor.id, "same")
        assert db_error(exc.value)[0] == "config_version_has_changes"

    def test_blank_comment_is_rejected(self, configuration, editor):
        with pytest.raises(IntegrityError) as exc, transaction.atomic():
            queries.save_version(configuration, {**VALID_DATA, "hours": 2}, editor.id, "  ")
        assert db_error(exc.value)[0] == "config_version_comment_not_blank"

    def test_created_at_comes_from_the_database_clock(self, configuration, editor):
        execute(
            "INSERT INTO config_version (configuration_id, data, comment, created_at) VALUES (%s, %s::jsonb, 'x', '2000-01-01')",
            [configuration, json.dumps({**VALID_DATA, "hours": 4})],
        )
        assert fetch_one("SELECT created_at FROM config_version WHERE number = 2")["created_at"].year > 2000

    def test_backdating_allowed_only_with_setting(self, configuration):
        execute("SET LOCAL confighub.allow_backdate = 'on'")
        execute(
            "INSERT INTO config_version (configuration_id, data, comment, created_at) VALUES (%s, %s::jsonb, 'x', '2000-01-01')",
            [configuration, json.dumps({**VALID_DATA, "hours": 4})],
        )
        assert fetch_one("SELECT created_at FROM config_version WHERE number = 2")["created_at"].year == 2000


class TestImmutability:
    @pytest.mark.parametrize("sql", ["UPDATE config_version SET comment = 'x'", "DELETE FROM config_version"])
    def test_versions_cannot_change(self, configuration, sql):
        with pytest.raises(IntegrityError, match="immutable"), transaction.atomic():
            execute(sql)

    def test_configuration_data_cannot_be_edited_directly(self, configuration):
        with pytest.raises(IntegrityError, match="inserting a config_version"), transaction.atomic():
            execute("UPDATE configuration SET data = '{}' WHERE id = %s", [configuration])
        with pytest.raises(IntegrityError), transaction.atomic():
            execute("UPDATE configuration SET version = 5 WHERE id = %s", [configuration])

    def test_new_configuration_must_start_empty(self, product, second_customer):
        with pytest.raises(IntegrityError, match="starts empty"), transaction.atomic():
            execute(
                "INSERT INTO configuration (product_id, client_id, data) VALUES (%s, %s, '{\"hours\": 1}')",
                [product.id, second_customer.id],
            )

    def test_status_can_change(self, configuration):
        assert queries.toggle_status(configuration) == "disabled"
        assert queries.toggle_status(configuration) == "active"


class TestRestoreAndChanges:
    def test_restore_creates_new_version(self, configuration, editor, manager):
        first = queries.configuration_versions(configuration)[0]["id"]
        queries.save_version(configuration, {**VALID_DATA, "hours": 9}, editor.id, "nine")
        assert queries.restore_version(first, manager.id) == 3
        latest = queries.configuration_versions(configuration)[0]
        assert latest["comment"] == "Restored version 1" and latest["data"]["hours"] == 6

    def test_restore_of_current_data_is_refused(self, configuration, manager):
        first = queries.configuration_versions(configuration)[0]["id"]
        with pytest.raises(IntegrityError), transaction.atomic():
            queries.restore_version(first, manager.id)

    def test_version_changes(self, configuration, editor):
        first_id = queries.configuration_versions(configuration)[0]["id"]
        first = queries.version_changes(first_id)
        # Version 1 lists every key that has a value, in schema order; JSON null counts as no value.
        assert [c["key"] for c in first] == ["path", "hours", "discount", "promo", "currency"]
        queries.save_version(configuration, {**VALID_DATA, "hours": 9, "start": "2026-01-01"}, editor.id, "x")
        second = queries.version_changes(queries.configuration_versions(configuration)[0]["id"])
        assert second == [{"key": "hours", "old": 6, "new": 9}, {"key": "start", "old": None, "new": "2026-01-01"}]

    def test_overview_marks_current_version(self, configuration, editor):
        queries.save_version(configuration, {**VALID_DATA, "hours": 9}, editor.id, "x")
        flags = [(v["number"], v["is_current"]) for v in queries.configuration_versions(configuration)]
        assert flags == [(2, True), (1, False)]

