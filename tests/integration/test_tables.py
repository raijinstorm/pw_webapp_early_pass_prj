"""The two filterable tables (configurations and history), the dashboard, and HTMX partial responses."""

import json
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from app import queries
from app.db import execute
from app.models import Client
from tests.conftest import VALID_DATA

pytestmark = pytest.mark.django_db
HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def two_products(configuration, other_product, second_customer, admin_user):
    """Editor sees 'pricing' only; a disabled 'forecast' config exists that they must not see."""
    execute("INSERT INTO schema_field (product_id, key, label, field_type) VALUES (%s, 'x', 'X', 'integer')", [other_product.id])
    hidden = queries.create_configuration(other_product.id, second_customer.id, {"x": 1}, admin_user.id, "hidden change")
    queries.toggle_status(hidden)
    return configuration, hidden


def rows(response):
    return list(response.context["page"].object_list)


def client_names(response):
    return [r["client_name"] for r in rows(response)]


class TestConfigTable:
    def test_shows_only_visible_configurations(self, client, editor, two_products):
        client.force_login(editor)
        response = client.get(reverse("config_list"))
        assert client_names(response) == ["Acme"]
        assert b"<html" in response.content

    def test_admin_sees_everything(self, client, admin_user, two_products):
        client.force_login(admin_user)
        assert len(rows(client.get(reverse("config_list")))) == 2

    @pytest.mark.parametrize(
        "params, expected",
        [
            ({"product": "forecast"}, ["Globex"]),
            ({"status": "active"}, ["Acme"]),
            ({"status": "disabled"}, ["Globex"]),
            ({"q": "glob"}, ["Globex"]),
            ({"q": "zzz"}, []),
        ],
    )
    def test_filters(self, client, admin_user, two_products, params, expected):
        client.force_login(admin_user)
        assert client_names(client.get(reverse("config_list"), params)) == expected

    def test_filter_by_client(self, client, admin_user, two_products, customer):
        client.force_login(admin_user)
        assert client_names(client.get(reverse("config_list"), {"client": customer.id})) == ["Acme"]

    def test_invalid_filter_values_are_ignored(self, client, editor, two_products):
        client.force_login(editor)
        response = client.get(reverse("config_list"), {"product": "forecast", "client": "abc"})
        assert response.status_code == 200
        assert client_names(response) == ["Acme"]

    def test_htmx_request_returns_only_the_table(self, client, editor, two_products):
        client.force_login(editor)
        response = client.get(reverse("config_list"), {"status": "active"}, **HTMX)
        assert b"<html" not in response.content
        assert b"<table" in response.content

    def test_pagination(self, client, admin_user, product, editor):
        for i in range(20):
            customer = Client.objects.create(name=f"Client {i:02d}")
            queries.create_configuration(product.id, customer.id, VALID_DATA, editor.id, "seed")
        client.force_login(admin_user)
        first = client.get(reverse("config_list"), {"product": "pricing"})
        assert len(rows(first)) == 15
        assert b"Next" in first.content
        assert len(rows(client.get(reverse("config_list"), {"product": "pricing", "page": 2}))) == 5


class TestHistoryTable:
    def test_shows_only_visible_versions(self, client, editor, two_products):
        client.force_login(editor)
        assert [v["comment"] for v in rows(client.get(reverse("history_list")))] == ["Initial configuration"]

    def test_filter_by_author_and_product(self, client, admin_user, editor, two_products):
        client.force_login(admin_user)
        by_author = client.get(reverse("history_list"), {"author": editor.username})
        assert [v["author"] for v in rows(by_author)] == ["eddie"]
        by_product = client.get(reverse("history_list"), {"product": "forecast"})
        assert [v["comment"] for v in rows(by_product)] == ["hidden change"]

    def test_filter_by_dates(self, client, editor, configuration):
        execute("SET LOCAL confighub.allow_backdate = 'on'")
        execute(
            "INSERT INTO config_version (configuration_id, data, comment, created_at) VALUES (%s, %s::jsonb, 'old change', %s)",
            [configuration, json.dumps({**VALID_DATA, "hours": 3}), timezone.now() - timedelta(days=30)],
        )
        client.force_login(editor)
        today = timezone.localdate()
        recent = client.get(reverse("history_list"), {"date_from": today - timedelta(days=1)})
        assert [v["comment"] for v in rows(recent)] == ["Initial configuration"]
        older = client.get(reverse("history_list"), {"date_to": today - timedelta(days=10)})
        assert [v["comment"] for v in rows(older)] == ["old change"]

    def test_invalid_date_range_shows_message(self, client, editor, configuration):
        client.force_login(editor)
        response = client.get(reverse("history_list"), {"date_from": "2026-10-02", "date_to": "2026-10-01"}, **HTMX)
        assert b"must be on or after" in response.content
        assert b"<html" not in response.content


class TestDashboard:
    def test_lists_products_with_role_and_recent_changes(self, client, manager, configuration):
        client.force_login(manager)
        response = client.get(reverse("dashboard"))
        [product] = response.context["products"]
        assert product["role"] == "manager" and product["config_count"] == 1
        assert [v["configuration_id"] for v in response.context["recent"]] == [configuration]

    def test_admin_role_and_empty_state(self, client, admin_user, outsider, product):
        client.force_login(admin_user)
        assert client.get(reverse("dashboard")).context["products"][0]["role"] == "admin"
        client.force_login(outsider)
        assert b"not a member of any product" in client.get(reverse("dashboard")).content
