import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from app import queries
from app.db import fetch_value
from tests.conftest import form_data
pytestmark = pytest.mark.django_db
HTMX = {'HTTP_HX_REQUEST': 'true'}

def messages_of(response):
    return [str(m) for m in get_messages(response.wsgi_request)]

def version_count():
    return fetch_value('SELECT count(*) FROM config_version')

class TestCreate:

    def test_create_configuration(self, client, editor, product, customer):
        client.force_login(editor)
        response = client.post(reverse('config_create', args=[product.code]), form_data(client=customer.id))
        [row] = queries.configurations(editor.id)
        assert response.status_code == 302 and response.url == reverse('config_detail', args=[row['id']])
        assert row['version'] == 1 and row['data']['hours'] == 6 and (row['updated_by'] == 'eddie')

    def test_database_rejects_invalid_values(self, client, editor, product, customer):
        client.force_login(editor)
        response = client.post(reverse('config_create', args=[product.code]), form_data(client=customer.id, value__path='C:\\x', value__hours='99', value__currency=''))
        assert response.status_code == 200
        errors = response.context['form'].errors
        assert errors['value__path'][0].startswith('Must match the pattern')
        assert errors['value__hours'] == ['Must be at most 24.']
        assert errors['value__currency'] == ['This field is required.']
        assert queries.configurations(editor.id) == []

    def test_client_taken_in_the_meantime(self, client, editor, product, customer, configuration):
        client.force_login(editor)
        response = client.post(reverse('config_create', args=[product.code]), form_data(client=customer.id))
        assert 'client' in response.context['form'].errors

    def test_product_without_schema_redirects(self, client, admin_user, other_product):
        client.force_login(admin_user)
        response = client.get(reverse('config_create', args=[other_product.code]))
        assert response.status_code == 302
        assert 'no schema fields' in messages_of(response)[0]

class TestEdit:

    def test_edit_creates_new_version(self, client, editor, configuration):
        client.force_login(editor)
        response = client.post(reverse('config_edit', args=[configuration]), form_data(value__hours='12', value__promo=None))
        row = queries.configuration(configuration)
        assert response.status_code == 302
        assert row['version'] == 2 and row['data']['hours'] == 12 and (row['data']['promo'] is False)
        assert 'Saved as version 2' in messages_of(response)[0]

    def test_edit_without_changes_is_refused_by_the_database(self, client, editor, configuration):
        client.force_login(editor)
        response = client.post(reverse('config_edit', args=[configuration]), form_data())
        assert response.status_code == 200
        assert b'Nothing changed' in response.content
        assert version_count() == 1

    def test_edit_page_shows_current_values(self, client, editor, configuration):
        client.force_login(editor)
        assert b'value="/mnt/acme"' in client.get(reverse('config_edit', args=[configuration])).content

class TestDetailAndVersions:

    def test_detail_page(self, client, editor, configuration):
        client.force_login(editor)
        response = client.get(reverse('config_detail', args=[configuration]))
        assert response.status_code == 200
        assert len(response.context['rows']) == 6
        assert not response.context['can_manage']

    def test_version_detail_shows_changes(self, client, editor, configuration):
        queries.save_version(configuration, {**queries.configuration(configuration)['data'], 'hours': 9}, editor.id, 'nine')
        latest = queries.configuration_versions(configuration)[0]
        client.force_login(editor)
        response = client.get(reverse('version_detail', args=[latest['id']]), **HTMX)
        assert response.context['changes'] == [{'key': 'hours', 'old': 6, 'new': 9}]
        assert b'<html' not in response.content

    def test_restore_old_version(self, client, manager, configuration):
        first = queries.configuration_versions(configuration)[0]
        queries.save_version(configuration, {**first['data'], 'hours': 9}, manager.id, 'nine')
        client.force_login(manager)
        response = client.post(reverse('version_restore', args=[first['id']]))
        row = queries.configuration(configuration)
        assert response.status_code == 302
        assert row['version'] == 3 and row['data']['hours'] == 6
        assert 'restored as version 3' in messages_of(response)[0]

    def test_restore_refused_by_the_database(self, client, manager, configuration):
        client.force_login(manager)
        first = queries.configuration_versions(configuration)[0]
        response = client.post(reverse('version_restore', args=[first['id']]))
        assert "can't be restored: Nothing changed" in messages_of(response)[0]
        assert version_count() == 1

class TestStatus:

    def test_toggle_with_htmx_returns_partial(self, client, manager, configuration):
        client.force_login(manager)
        response = client.post(reverse('config_toggle_status', args=[configuration]), **HTMX)
        assert queries.configuration(configuration)['status'] == 'disabled'
        assert b'Activate' in response.content and b'<html' not in response.content

    def test_toggle_without_htmx_redirects(self, client, manager, configuration):
        client.force_login(manager)
        client.post(reverse('config_toggle_status', args=[configuration]))
        response = client.post(reverse('config_toggle_status', args=[configuration]))
        assert response.status_code == 302
        assert queries.configuration(configuration)['status'] == 'active'
