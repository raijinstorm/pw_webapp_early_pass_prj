"""Settings for the test suite.

Tests run against a real PostgreSQL, because the business logic lives in PL/pgSQL (sql/).
Start the throwaway test database first: docker compose -f docker-compose.test.yml up -d
"""

import os

os.environ.setdefault("SECRET_KEY", "tests-only-secret-key")

from .settings import *  # noqa: E402,F403
from .settings import STORAGES  # noqa: E402

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "confighub",
        "USER": "confighub",
        "PASSWORD": "test-only",
        "HOST": os.environ.get("TEST_POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("TEST_POSTGRES_PORT", "5433"),
    }
}

# The manifest storage needs collectstatic to have run; tests don't need hashed file names.
STORAGES = {**STORAGES, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}

# A fast hasher keeps user-creating tests quick. Never use outside tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
