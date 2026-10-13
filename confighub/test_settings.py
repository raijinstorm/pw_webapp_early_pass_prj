import os
os.environ.setdefault('SECRET_KEY', 'tests-only-secret-key')
from .settings import *
from .settings import STORAGES
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'confighub', 'USER': 'confighub', 'PASSWORD': 'test-only', 'HOST': os.environ.get('TEST_POSTGRES_HOST', '127.0.0.1'), 'PORT': os.environ.get('TEST_POSTGRES_PORT', '5433')}}
STORAGES = {**STORAGES, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
