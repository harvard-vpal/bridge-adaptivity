# flake8: noqa: F405
from config.settings.base import *  # noqa: F403

os.environ.setdefault('ENV_TYPE', 'local')

DEBUG = True
LTI_SSL = False

INSTALLED_APPS += ('debug_toolbar', 'sslserver')

MIDDLEWARE_CLASSES += (
    'djdev_panel.middleware.DebugMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = normpath(join(SITE_ROOT, 'http_static'))

# For Django Debug Toolbar:
# NOTE(idegtiarov) In order to make dgango-debug-toolbar works with docker add here docker machine ip address.
# Docker container's ip address could be found in the output of the command: > docker inspect <container_id>
INTERNAL_IPS = ('127.0.0.1', '172.19.0.1')

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

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
APPS_TO_LOG = ['bridge_lti', 'module', 'api']
APP_LOGGERS = {}
for app in APPS_TO_LOG:
    APP_LOGGERS[app] = {
        'handlers': ['console', 'logfile'],
        'level': 'DEBUG',
        'propagate': True,
    }
LOGGING['loggers'].update(APP_LOGGERS)
