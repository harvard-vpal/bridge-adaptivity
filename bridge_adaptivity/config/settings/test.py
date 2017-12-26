# coding: utf-8

from base import *  # noqa: F401,F403

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}

SECRET_KEY = 'KEY'

DEBUG = True

EMAIL_USE_TLS = True
EMAIL_HOST = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587
EMAIL_FROM = ''
