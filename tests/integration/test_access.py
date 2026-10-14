import pytest
from django.urls import reverse
from app import queries
pytestmark = pytest.mark.django_db

def urls(configuration, product):
    field = queries.schema_fields(product.id)[0]
    version = queries.configuration_versions(configuration)[0]
    return {'product': reverse('product_detail', args=[product.code]), 'config': reverse('config_detail', args=[configuration]), 'edit': reverse('config_edit', args=[configuration]), 'create': reverse('config_create', args=[product.code]), 'version': reverse('version_detail', args=[version['id']]), 'field_new': reverse('field_create', args=[product.code]), 'field_edit': reverse('field_edit', args=[product.code, field['id']]), 'field_delete': reverse('field_delete', args=[product.code, field['id']])}

def test_outsider_cannot_see_product_data(client, outsider, configuration, product):
    client.force_login(outsider)
    for (name, url) in urls(configuration, product).items():
        assert client.get(url).status_code == 403, name
    assert b'Access denied' in client.get(urls(configuration, product)['product']).content

def test_editor_can_view_and_edit_but_not_manage(client, editor, configuration, product):
    client.force_login(editor)
    u = urls(configuration, product)
    for name in ['product', 'config', 'edit', 'create', 'version']:
        assert client.get(u[name]).status_code == 200, name
    for name in ['field_new', 'field_edit', 'field_delete']:
        assert client.get(u[name]).status_code == 403, name
    version = queries.configuration_versions(configuration)[0]
    assert client.post(reverse('config_toggle_status', args=[configuration])).status_code == 403
    assert client.post(reverse('version_restore', args=[version['id']])).status_code == 403
    assert client.post(reverse('member_add', args=[product.code]), {'username': 'x', 'role': 'editor'}).status_code == 403

@pytest.mark.parametrize('user_fixture', ['manager', 'admin_user'])
def test_manager_and_admin_can_manage(client, request, user_fixture, configuration, product):
    client.force_login(request.getfixturevalue(user_fixture))
    for (name, url) in urls(configuration, product).items():
        assert client.get(url).status_code == 200, name

def test_admin_site_only_for_admins(client, editor, admin_user):
    client.force_login(editor)
    assert client.get('/admin/').status_code == 302
    client.force_login(admin_user)
    assert client.get('/admin/').status_code == 200

def test_missing_objects_return_404(client, editor, product):
    client.force_login(editor)
    assert client.get('/products/missing/').status_code == 404
    assert client.get('/configs/999999/').status_code == 404
    assert client.get('/versions/999999/').status_code == 404
    assert client.get(f'/products/{product.code}/fields/999999/edit/').status_code in (403, 404)
    assert b"doesn't exist" in client.get('/configs/999999/').content

def test_write_endpoints_reject_get(client, manager, configuration):
    client.force_login(manager)
    assert client.get(reverse('config_toggle_status', args=[configuration])).status_code == 405
