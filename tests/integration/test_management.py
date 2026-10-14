"""Manager features (schema fields, members), the admin site and the demo data command."""

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse

from app import queries
from app.db import fetch_value
from app.models import Membership, User

pytestmark = pytest.mark.django_db
HTMX = {"HTTP_HX_REQUEST": "true"}


def field(product, key):
    return next(f for f in queries.schema_fields(product.id) if f["key"] == key)


class TestSchemaFields:
    def test_create_field(self, client, manager, product):
        client.force_login(manager)
        data = {"key": "region", "label": "Region", "field_type": "choice", "choices": "EU,US", "required": "on", "position": 9}
        response = client.post(reverse("field_create", args=[product.code]), data)
        assert response.status_code == 302
        assert field(product, "region")["choices"] == ["EU", "US"]

    @pytest.mark.parametrize(
        "data, error_field, message",
        [
            ({"key": "Bad Key", "field_type": "text"}, "key", "Use lowercase letters"),
            ({"key": "hours", "field_type": "text"}, "key", "already has a field"),
            ({"key": "n", "field_type": "integer", "min_value": "5", "max_value": "1"}, "max_value", "Max must be"),
            ({"key": "n", "field_type": "text", "min_value": "1"}, "min_value", "only apply to Integer"),
            ({"key": "n", "field_type": "choice", "choices": "one"}, "choices", "at least two"),
            ({"key": "n", "field_type": "choice"}, "choices", "need options"),
            ({"key": "n", "field_type": "text", "pattern": "("}, "pattern", "not a valid regular expression"),
            ({"key": "n", "field_type": "integer", "pattern": "x"}, "pattern", "only applies to Text"),
        ],
    )
    def test_database_rules_shown_on_the_form(self, client, manager, product, data, error_field, message):
        client.force_login(manager)
        response = client.post(reverse("field_create", args=[product.code]), {"label": "N", "position": 0, **data})
        assert response.status_code == 200
        assert message in response.context["form"].errors[error_field][0]

    def test_edit_field_keeps_key(self, client, manager, product):
        hours = field(product, "hours")
        client.force_login(manager)
        data = {"key": "renamed", "label": "Hours (new)", "field_type": "integer", "min_value": 1, "max_value": 48,
                "position": 1, "required": "on"}
        assert client.post(reverse("field_edit", args=[product.code, hours["id"]]), data).status_code == 302
        updated = field(product, "hours")
        assert updated["label"] == "Hours (new)" and updated["max_value"] == 48

    def test_delete_field(self, client, manager, product):
        start = field(product, "start")
        client.force_login(manager)
        assert client.get(reverse("field_delete", args=[product.code, start["id"]])).status_code == 200
        client.post(reverse("field_delete", args=[product.code, start["id"]]))
        assert "start" not in [f["key"] for f in queries.schema_fields(product.id)]

    def test_field_of_other_product_is_404(self, client, admin_user, product, other_product):
        client.force_login(admin_user)
        hours = field(product, "hours")
        assert client.get(reverse("field_edit", args=[other_product.code, hours["id"]])).status_code == 404


class TestMembers:
    def test_add_member_with_htmx(self, client, manager, outsider, product):
        client.force_login(manager)
        response = client.post(reverse("member_add", args=[product.code]), {"username": "olga", "role": "editor"}, **HTMX)
        assert queries.user_role(outsider.id, product.id) == "editor"
        assert b"olga" in response.content and b"<html" not in response.content

    def test_add_unknown_user_shows_error(self, client, manager, product):
        client.force_login(manager)
        response = client.post(reverse("member_add", args=[product.code]), {"username": "ghost", "role": "editor"}, **HTMX)
        assert b"No active user" in response.content

    def test_add_existing_member_rejected_by_database(self, client, manager, editor, product):
        client.force_login(manager)
        response = client.post(reverse("member_add", args=[product.code]), {"username": "eddie", "role": "manager"}, **HTMX)
        assert b"already a member" in response.content
        assert queries.user_role(editor.id, product.id) == "editor"

    def test_add_member_without_htmx_redirects(self, client, manager, outsider, product):
        client.force_login(manager)
        response = client.post(reverse("member_add", args=[product.code]), {"username": "olga", "role": "manager"})
        assert response.status_code == 302

    def test_remove_member(self, client, manager, editor, product):
        membership = Membership.objects.get(user=editor)
        client.force_login(manager)
        assert client.post(reverse("member_remove", args=[membership.pk]), **HTMX).status_code == 200
        assert queries.user_role(editor.id, product.id) is None

    def test_cannot_remove_yourself(self, client, manager, product):
        membership = Membership.objects.get(user=manager)
        client.force_login(manager)
        assert client.post(reverse("member_remove", args=[membership.pk])).status_code == 302
        assert queries.user_role(manager.id, product.id) == "manager"


class TestAdminSite:
    def test_admin_pages_load(self, client, admin_user, configuration, manager, product):
        client.force_login(admin_user)
        # Memberships have no page of their own: they are edited inline on users and products.
        for model in ["user", "product", "client", "configuration", "configversion"]:
            assert client.get(f"/admin/app/{model}/").status_code == 200, model
        assert client.get(f"/admin/app/product/{product.pk}/change/").status_code == 200
        assert client.get(f"/admin/app/user/{manager.pk}/change/").status_code == 200

    def test_history_is_read_only_and_nothing_is_deleted(self, client, admin_user, configuration, product):
        client.force_login(admin_user)
        assert client.get("/admin/app/configversion/add/").status_code == 403
        assert client.get(f"/admin/app/product/{product.pk}/delete/").status_code == 403

    def test_admin_creates_product_through_database_rules(self, client, admin_user):
        client.force_login(admin_user)
        data = {"code": "new-feed", "name": "New Feed", "description": "",
                "memberships-TOTAL_FORMS": 0, "memberships-INITIAL_FORMS": 0}
        assert client.post("/admin/app/product/add/", data).status_code == 302
        assert queries.product_by_code("new-feed")["name"] == "New Feed"


class TestSeedCommand:
    def test_creates_demo_data_once(self, monkeypatch, db):
        monkeypatch.setenv("DEMO_PASSWORD", "Seed-pass-123")
        call_command("seed_demo")
        assert User.objects.filter(is_superuser=True).count() == 1
        assert fetch_value("SELECT count(*) FROM product") == 3
        assert fetch_value("SELECT count(*) FROM configuration") == 18
        # Every demo version passed the schema check in the trigger, and history is consistent.
        assert fetch_value("SELECT count(*) FROM configuration c WHERE c.version <> (SELECT max(number) FROM config_version v WHERE v.configuration_id = c.id)") == 0
        assert User.objects.get(username="anna").check_password("Seed-pass-123")
        call_command("seed_demo")  # second run is skipped
        assert fetch_value("SELECT count(*) FROM product") == 3

    def test_requires_password(self, monkeypatch, db):
        monkeypatch.delenv("DEMO_PASSWORD", raising=False)
        with pytest.raises(CommandError):
            call_command("seed_demo")
