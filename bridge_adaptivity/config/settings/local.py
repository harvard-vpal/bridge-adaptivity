# flake8: noqa: F405
from config.settings.base import *  # noqa: F403

TEST_RUNNER = 'config.test_runner.PytestTestRunner'

SECRET_KEY = secure.SECRET_KEY

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

DEBUG = True
LTI_SSL = False

INSTALLED_APPS += ('debug_toolbar', 'sslserver')

MIDDLEWARE += [
    'djdev_panel.middleware.DebugMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

STATIC_URL = '/static/'
STATIC_ROOT = normpath(join(SITE_ROOT, 'static'))

# For Django Debug Toolbar:
# NOTE(idegtiarov) In order to make dgango-debug-toolbar works with docker add here docker machine ip address.
# Docker container's ip address could be found in the output of the command: > docker inspect <container_id>
INTERNAL_IPS = ('127.0.0.1', '172.19.0.1')

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

ALLOWED_HOSTS = secure.ALLOWED_HOSTS

# Celery settings
AMQP_PASS = secure.AMQP_PASS
AMQP_USER = secure.AMQP_USER

CELERY_BROKER_URL = 'amqp://{}:{}@rabbit//'.format(AMQP_USER, AMQP_PASS)

# Logging settings
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': SITE_ROOT + "/dev.log",
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
APPS_TO_LOG = ['api', 'bridge_lti', 'config', 'module', 'provider']
APP_LOGGERS = {}
for app in APPS_TO_LOG:
    APP_LOGGERS[app] = {
        'handlers': ['console', 'logfile'],
        'level': 'DEBUG',
        'propagate': True,
    }
LOGGING['loggers'].update(APP_LOGGERS)
