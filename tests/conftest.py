"""Shared fixtures: one product with a schema, users for every role, and a configuration with one version.

Reference rows are created with the ORM (they still go through the database constraints);
configurations are created with the SQL function create_configuration, like the app does.
"""

import pytest

from app import queries
from app.models import Client, Membership, Product, Role, SchemaField, User

PASSWORD = "Test-pass-123"

VALID_DATA = {"path": "/mnt/acme", "hours": 6, "discount": 10.5, "promo": True, "start": None, "currency": "EUR"}


def make_user(username, **extra):
    return User.objects.create_user(username, f"{username}@test.example.com", PASSWORD, **extra)


@pytest.fixture
def admin_user(db):
    return make_user("root", is_superuser=True, is_staff=True)


@pytest.fixture
def product(db):
    product = Product.objects.create(code="pricing", name="Pricing", description="Price files")
    fields = [
        dict(key="path", label="Path", field_type="text", pattern=r"^/mnt/[a-z/]+$"),
        dict(key="hours", label="Hours", field_type="integer", min_value=1, max_value=24),
        dict(key="discount", label="Discount", field_type="decimal", min_value=0, max_value=50),
        dict(key="promo", label="Promo", field_type="boolean", required=False),
        dict(key="start", label="Start", field_type="date", required=False),
        dict(key="currency", label="Currency", field_type="choice", choices=["EUR", "PLN"]),
    ]
    for position, f in enumerate(fields):
        SchemaField.objects.create(product=product, position=position, **f)
    return product


@pytest.fixture
def product_row(product):
    """The product as the views see it: a row from SQL."""
    return queries.product_by_code(product.code)


@pytest.fixture
def other_product(db):
    return Product.objects.create(code="forecast", name="Forecast")


@pytest.fixture
def manager(product):
    user = make_user("manny")
    Membership.objects.create(user=user, product=product, role=Role.MANAGER)
    return user


@pytest.fixture
def editor(product):
    user = make_user("eddie")
    Membership.objects.create(user=user, product=product, role=Role.EDITOR)
    return user


@pytest.fixture
def outsider(db):
    return make_user("olga")


@pytest.fixture
def customer(db):
    return Client.objects.create(name="Acme")


@pytest.fixture
def second_customer(db):
    return Client.objects.create(name="Globex")


@pytest.fixture
def configuration(product, customer, editor):
    """Configuration id of Pricing/Acme, at version 1."""
    return queries.create_configuration(product.id, customer.id, dict(VALID_DATA), editor.id, "Initial configuration")


def form_data(**overrides):
    """POST data for the configuration form, using the fixture schema. Pass None to leave a field out."""
    data = {
        "value__path": "/mnt/acme",
        "value__hours": "6",
        "value__discount": "10.5",
        "value__promo": "on",
        "value__start": "",
        "value__currency": "EUR",
        "comment": "test change",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}
