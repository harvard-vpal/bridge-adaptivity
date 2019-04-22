# coding: utf-8
from config.settings.local import *  # noqa: F401,F403

BRIDGE_HOST = 'localhost'
BRIDGE_HOST = BRIDGE_HOST.strip()

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

UPDATE_DATABASE = {'NAME': 'traviscidb', 'HOST': 'localhost'}

try:
    from . import secure
    UPDATE_DATABASE['PORT'] = 5430
except ImportError:
    from . import secure_example as secure

DATABASES = secure.DATABASES
DATABASES['default'].update(UPDATE_DATABASE)

SECRET_KEY = 'KEY'

DEBUG = False

# Disable versions of the static file for the tests
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

SELENIUM_DRIVER = 'Remote'

SELENIUM_HOST = 'chromedriver'

SELENIUM_TESTSERVER_HOST = 'bridge'

TEST_RUNNER = 'django_selenium.selenium_runner.SeleniumTestRunner'
