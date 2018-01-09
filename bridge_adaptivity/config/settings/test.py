# coding: utf-8
from base import *  # noqa: F401,F403

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

try:
    import secure
    DATABASES = secure.DATABASES
except ImportError:
    import secure_example
    DATABASES = secure_example.DATABASES

SECRET_KEY = 'KEY'

DEBUG = False
