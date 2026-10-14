import os
import pytest
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
from tests.conftest import PASSWORD

@pytest.fixture
def login(page, live_server):

    def _login(username):
        page.goto(f'{live_server.url}/accounts/login/')
        page.get_by_label('Username').fill(username)
        page.get_by_label('Password').fill(PASSWORD)
        page.get_by_role('button', name='Sign in').click()
        page.wait_for_url(f'{live_server.url}/')
        return page
    return _login
