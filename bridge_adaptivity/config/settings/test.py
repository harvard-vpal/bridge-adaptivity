# coding: utf-8
from base import *  # noqa: F401,F403

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

try:
    import secure
    DATABASES = secure.DATABASES
except ImportError:
    import secure_example
    DATABASES = secure_example.DATABASES

if 'ISLOCAL' not in os.environ:
    # assume that we are in travis-ci
    DATABASES['default'].update({'NAME': 'traviscidb', 'HOST': 'localhost'})

SECRET_KEY = 'KEY'

DEBUG = False
