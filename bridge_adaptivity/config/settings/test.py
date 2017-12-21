# coding: utf-8

from base import * # flake8: noqa: F401

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}

SECRET_KEY = 'KEY'

DEBUG = True
LTI_DEBUG = True
