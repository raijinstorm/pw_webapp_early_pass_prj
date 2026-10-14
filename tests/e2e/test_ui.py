import pytest
from playwright.sync_api import expect
from app import queries
from tests.conftest import VALID_DATA
pytestmark = pytest.mark.django_db(transaction=True)

def test_login_shows_dashboard(login, configuration):
    page = login('eddie')
    expect(page.get_by_role('heading', name='Hello, eddie')).to_be_visible()
    expect(page.get_by_text('Pricing').first).to_be_visible()

def test_wrong_password_stays_on_login(page, live_server, editor):
    page.goto(f'{live_server.url}/accounts/login/')
    page.get_by_label('Username').fill('eddie')
    page.get_by_label('Password').fill('wrong-password')
    page.get_by_role('button', name='Sign in').click()
    expect(page.get_by_text('Please enter a correct username and password')).to_be_visible()

def test_filter_table_without_reload(login, live_server, configuration, second_customer, product, editor):
    disabled = queries.create_configuration(product.id, second_customer.id, VALID_DATA, editor.id, 'x')
    queries.toggle_status(disabled)
    page = login('eddie')
    page.goto(f'{live_server.url}/configs/')
    expect(page.locator('#results tbody tr')).to_have_count(2)
    page.evaluate('window.notReloaded = true')
    page.locator('select[name=status]').select_option('disabled')
    expect(page.locator('#results tbody tr')).to_have_count(1)
    expect(page.locator('#results')).to_contain_text('Globex')
    assert page.evaluate('window.notReloaded') is True
    assert 'status=disabled' in page.url

def test_edit_validation_and_new_version(login, live_server, configuration):
    page = login('eddie')
    page.goto(f'{live_server.url}/configs/{configuration}/edit/')
    page.get_by_label('Path').fill('C:\\wrong')
    page.get_by_label('Change comment').fill('try a bad path')
    page.get_by_role('button', name='Save new version').click()
    expect(page.get_by_text('Must match the pattern')).to_be_visible()
    page.get_by_label('Path').fill('/mnt/acme/new')
    page.get_by_role('button', name='Save new version').click()
    expect(page.get_by_text('Saved as version 2.')).to_be_visible()
    expect(page.get_by_text('/mnt/acme/new')).to_be_visible()

def test_version_diff_loads_inline(login, live_server, configuration, editor):
    queries.save_version(configuration, {**VALID_DATA, 'hours': 9}, editor.id, 'nine hours')
    page = login('eddie')
    page.goto(f'{live_server.url}/configs/{configuration}/')
    page.get_by_role('button', name='nine hours').click()
    panel = page.locator('#version-detail')
    expect(panel).to_contain_text('Version 2')
    expect(panel.locator('.diff-new')).to_have_text('9')

def test_manager_toggles_status_inline(login, live_server, configuration, manager):
    page = login('manny')
    page.goto(f'{live_server.url}/configs/{configuration}/')
    page.get_by_role('button', name='Disable').click()
    expect(page.locator('#status')).to_contain_text('Disabled')
    expect(page.get_by_role('button', name='Activate')).to_be_visible()

def test_responsive_navigation(login, live_server, configuration):
    page = login('eddie')
    page.set_viewport_size({'width': 1280, 'height': 800})
    expect(page.get_by_role('button', name='Menu')).to_be_hidden()
    expect(page.get_by_role('link', name='History', exact=True)).to_be_visible()
    page.set_viewport_size({'width': 375, 'height': 812})
    expect(page.get_by_role('link', name='History', exact=True)).to_be_hidden()
    page.get_by_role('button', name='Menu').click()
    expect(page.get_by_role('link', name='History', exact=True)).to_be_visible()

def test_password_reset_from_login_page(page, live_server, editor):
    page.goto(f'{live_server.url}/accounts/login/')
    page.get_by_role('link', name='Forgot your password?').click()
    page.get_by_label('Email').fill(editor.email)
    page.get_by_role('button', name='Send reset link').click()
    expect(page.get_by_role('heading', name='Check your email')).to_be_visible()
