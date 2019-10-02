"""
Django settings for adaptive_edx project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from os.path import abspath, basename, dirname, join, normpath
from sys import path

try:
    from . import secure
except ImportError:
    from . import secure_example as secure

# Sentry monitoring initialization
if secure.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=secure.SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()]
    )

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Absolute filesystem path to the Django project config directory:
DJANGO_PROJECT_CONFIG = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_PROJECT_CONFIG)

# Site name:
SITE_NAME = basename(SITE_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(SITE_ROOT)

DEBUG = False

ALLOWED_HOSTS = []

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # external apps
    'bootstrap3',
    'fontawesome',
    'corsheaders',
    'ordered_model',
    'rest_framework',
    'rest_framework.authtoken',
    'multiselectfield',
    'django_filters',
    'channels',

    # core functions
    'bridge_lti',
    'module',
    'api',
)

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [
        normpath(join(SITE_ROOT, 'templates')),
    ],
    'OPTIONS': {
        'context_processors': [
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.request',  # adds `request` object to templates context
            'django.contrib.messages.context_processors.messages',
        ],
        'loaders': [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ],
        'debug': True,
    },
}]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATIC_URL = '/static/'

# django-bootstrap:
BOOTSTRAP3 = {
    'include_jquery': True,
    'jquery_url': '//code.jquery.com/jquery-3.3.1.min.js'
}

# allow post requests from edx
CORS_ORIGIN_ALLOW_ALL = True

AUTH_USER_MODEL = 'bridge_lti.BridgeUser'

LOGIN_URL = 'login'

LOGIN_REDIRECT_URL = 'module:group-list'


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
        'TIMEOUT': 86400,  # 1 day
    },
}

# Celery settings

# Timespan for running sync task in seconds
CELERY_DELAY_SYNC_TASK = 5 * 60  # default value is equal to 5 minutes
CELERY_RESULT_TIMEOUT = 30  # default value is equal 0.5 minute

#: Only add pickle to this list if your broker is secured
#: from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'amqp'
CELERY_TASK_RESULT_EXPIRES = 300  # 5 minutes

# This settings are related to module/egines and declare gradable problems
PROBLEM_ACTIVITY_TYPES = (
    'problem',
)

# NOTE(idegtiarov) `SESSION_COOKIE_SAMESITE` and `CSRF_COOKIE_SAMESITE` was added in Django 2.1 and has broken current
#  LTI session flow. The parameter is set to None to revert the previous behavior.
SESSION_COOKIE_SAMESITE = None
CSRF_COOKIE_SAMESITE = None

# Django Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        # for browsable api view usage
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

# Demo functionality
TEST_SEQUENCE_SUFFIX = 'test_sequence_suffix'

ASGI_APPLICATION = "config.routing.application"

# Use Redis as channel layer for django channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}
# Use for checking score and show congratulation message or not. Value must be between 0 to 1.
CONGRATULATION_SCORE_LEVEL = 0.95
