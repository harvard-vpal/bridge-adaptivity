"""
docker-compose deployment on production machine
"""

# flake8: noqa: F405
from base import *  # noqa: F401,F403
import secure

SECRET_KEY = secure.SECRET_KEY
ALLOWED_HOSTS = secure.ALLOWED_HOSTS
STATIC_ROOT = '/www/static/'
DATABASES = secure.DATABASES

# Configure Bridge host with is used for lis_outcome_service_url composition
BRIDGE_HOST = secure.BRIDGE_HOST

try:
    # Engine for Adaptivity configuration block
    # ENGINE_MODULE is a string with the path to the engine module
    ENGINE_MODULE = secure.ENGINE_MODULE

    # ENGINE_DRIVER is a string with the name of driver class in the engine module
    ENGINE_DRIVER = secure.ENGINE_DRIVER

    # ENGINE_SETTINGS is a dict, with the initial params for driver initialization
    ENGINE_SETTINGS = secure.ENGINE_SETTINGS
except AttributeError:
    # Default Mock engine will be used
    pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'logfile': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR + "/bridge-error.log",
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'logfile']
    },
}
