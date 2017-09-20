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

import secure

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

SECRET_KEY = secure.SECRET_KEY

DEBUG = False

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # external apps
    'bootstrap3',
    'corsheaders',
    'ordered_model',

    # core functions
    'bridge_lti',
    'module',
    'api',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

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

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    normpath(join(SITE_ROOT, 'static')),
)

STATIC_URL = '/static/'
STATIC_ROOT = secure.STATIC_ROOT

# django-bootstrap:
BOOTSTRAP3 = {
    'include_jquery': True,
    'jquery_url': '//code.jquery.com/jquery-3.2.1.min.js'
}

# allow post requests from edx
CORS_ORIGIN_ALLOW_ALL = True

AUTH_USER_MODEL = 'bridge_lti.BridgeUser'

LOGIN_URL = 'login'

LOGIN_REDIRECT_URL = 'module:collection-list'

ALLOWED_HOSTS = secure.ALLOWED_HOSTS

DATABASES = secure.DATABASES

# Configure Bridge host with is used for lis_outcome_service_url composition
BRIDGE_HOST = secure.BRIDGE_HOST


# Engine for Adaptivity configuration block
# ENGINE_MODULE is a string with the path to the engine module
ENGINE_MODULE = secure.ENGINE_MODULE

# ENGINE_DRIVER is a string with the name of driver class in the engine module
ENGINE_DRIVER = secure.ENGINE_DRIVER

# ENGINE_SETTINGS is a dict, with the initial params for driver initialization
ENGINE_SETTINGS = secure.ENGINE_SETTINGS

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
        'TIMEOUT': 86400,  # 1 day
    },
}

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
            'filename': BASE_DIR + "/../bridge-error.log",
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'logfile']
    },
}
