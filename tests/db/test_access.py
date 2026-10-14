"""Access functions (sql/003_access_and_reports.sql)."""

import pytest

from app import queries

pytestmark = pytest.mark.django_db


def test_user_role(admin_user, manager, editor, outsider, product):
    assert queries.user_role(admin_user.id, product.id) == "admin"
    assert queries.user_role(manager.id, product.id) == "manager"
    assert queries.user_role(editor.id, product.id) == "editor"
    assert queries.user_role(outsider.id, product.id) is None


def test_inactive_users_have_no_access(editor, product):
    editor.is_active = False
    editor.save()
    assert queries.user_role(editor.id, product.id) is None
    assert queries.visible_products(editor.id) == []


def test_visible_products(admin_user, editor, product, other_product, configuration):
    assert [p["code"] for p in queries.visible_products(admin_user.id)] == ["forecast", "pricing"]
    [visible] = queries.visible_products(editor.id)
    assert visible["code"] == "pricing" and visible["role"] == "editor" and visible["config_count"] == 1


def test_lists_only_show_visible_rows(editor, outsider, configuration):
    assert len(queries.configurations(editor.id)) == 1
    assert queries.configurations(outsider.id) == []
    assert len(queries.versions(editor.id)) == 1
    assert queries.versions(outsider.id) == []
    assert queries.history_authors(editor.id) == [{"author": "eddie"}]
