# coding: utf-8
from config.settings.local import *  # noqa: F401,F403

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

UPDATE_DATABASE = {'NAME': 'traviscidb'}

try:
    import secure
except ImportError:
    import secure_example as secure
    UPDATE_DATABASE['HOST'] = 'localhost'

DATABASES = secure.DATABASES
DATABASES['default'].update(UPDATE_DATABASE)

SECRET_KEY = 'KEY'

DEBUG = False
