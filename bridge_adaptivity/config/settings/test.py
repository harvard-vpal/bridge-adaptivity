# coding: utf-8
from config.settings.local import *  # noqa: F401,F403

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

UPDATE_DATABASE = {'NAME': 'traviscidb'}

try:
    from . import secure
except ImportError:
    from . import secure_example as secure
    # UPDATE_DATABASE.update({'HOST': 'localhost', 'PORT': 5430})
UPDATE_DATABASE.update({'HOST': 'localhost', 'PORT': 5430})

DATABASES = secure.DATABASES
DATABASES['default'].update(UPDATE_DATABASE)

SECRET_KEY = 'KEY'

DEBUG = False

# Disable versions of the static file for the tests
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
