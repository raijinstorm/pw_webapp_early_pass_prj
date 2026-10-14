import os

import pytest

# Playwright's sync API runs an event loop; Django refuses DB access from such a thread unless allowed.
# Safe here: the tests and the live server use separate threads and a test-only database.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from tests.conftest import PASSWORD  # noqa: E402


@pytest.fixture
def login(page, live_server):
    """Log in through the real login form and return the page."""

    def _login(username):
        page.goto(f"{live_server.url}/accounts/login/")
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill(PASSWORD)
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_url(f"{live_server.url}/")
        return page

    return _login
