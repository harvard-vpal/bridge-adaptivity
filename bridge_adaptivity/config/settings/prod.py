"""
docker-compose deployment on production machine
"""

# flake8: noqa: F405
from .base import *  # noqa: F401,F403

SECRET_KEY = secure.SECRET_KEY
ALLOWED_HOSTS = secure.ALLOWED_HOSTS
STATIC_ROOT = '/www/static/'
DATABASES = secure.DATABASES

# Configure Bridge host with is used for lis_outcome_service_url composition
BRIDGE_HOST = secure.BRIDGE_HOST

# Celery settings
AMQP_PASS = secure.AMQP_PASS
AMQP_USER = secure.AMQP_USER

CELERY_BROKER_URL = 'amqp://{}:{}@rabbit//'.format(AMQP_USER, AMQP_PASS)

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
