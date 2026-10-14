import re
from datetime import timedelta
from unittest.mock import patch
import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from tests.conftest import PASSWORD
pytestmark = pytest.mark.django_db

@pytest.mark.parametrize('url', ['/', '/configs/', '/history/', '/products/pricing/', '/configs/1/'])
def test_anonymous_users_are_sent_to_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.url.startswith(reverse('login'))

def test_login_page_and_successful_login(client, editor):
    assert client.get(reverse('login')).status_code == 200
    response = client.post(reverse('login'), {'username': 'eddie', 'password': PASSWORD})
    assert response.status_code == 302 and response.url == reverse('dashboard')
    assert client.get(reverse('dashboard')).status_code == 200

def test_wrong_password_is_rejected(client, editor):
    response = client.post(reverse('login'), {'username': 'eddie', 'password': 'wrong'})
    assert response.status_code == 200
    assert b'Please enter a correct username and password' in response.content

def test_logout(client, editor):
    client.force_login(editor)
    response = client.post(reverse('logout'))
    assert response.status_code == 302
    assert client.get('/').status_code == 302

def test_password_reset_full_flow(client, editor):
    response = client.post(reverse('password_reset'), {'email': editor.email})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == 'Reset your ConfigHub password'
    assert 'valid for one hour' in mail.outbox[0].body
    link = re.search('http://testserver(/accounts/reset/\\S+)', mail.outbox[0].body).group(1)
    set_password_url = client.get(link).url
    response = client.post(set_password_url, {'new_password1': 'Brand-new-pass-77', 'new_password2': 'Brand-new-pass-77'})
    assert response.status_code == 302 and response.url == reverse('password_reset_complete')
    client.logout()
    assert client.login(username='eddie', password='Brand-new-pass-77')

def test_password_reset_unknown_email_sends_nothing(client):
    response = client.post(reverse('password_reset'), {'email': 'nobody@test.example.com'})
    assert response.status_code == 302
    assert mail.outbox == []

def test_invalid_reset_link(client):
    response = client.get('/accounts/reset/xx/bad-token/')
    assert b'invalid or has already been used' in response.content

def test_password_change(client, editor):
    client.force_login(editor)
    assert client.get(reverse('password_change')).status_code == 200
    response = client.post(reverse('password_change'), {'old_password': PASSWORD, 'new_password1': 'Another-pass-55', 'new_password2': 'Another-pass-55'})
    assert response.status_code == 302
    editor.refresh_from_db()
    assert editor.check_password('Another-pass-55')

def test_reset_link_expires_after_one_hour(editor, settings):
    assert settings.PASSWORD_RESET_TIMEOUT == 3600
    token = default_token_generator.make_token(editor)
    assert default_token_generator.check_token(editor, token)
    later = default_token_generator._now() + timedelta(hours=1, minutes=1)
    with patch.object(type(default_token_generator), '_now', return_value=later):
        assert not default_token_generator.check_token(editor, token)
