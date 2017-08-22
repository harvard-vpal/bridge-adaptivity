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
from django.core.urlresolvers import reverse_lazy
from sys import path
import secure

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Absolute filesystem path to the Django project config directory:
# (this is the parent of the directory where this file resides,
# since this file is now inside a 'settings' pacakge directory)
DJANGO_PROJECT_CONFIG = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
# (this is one directory up from the project config directory)
SITE_ROOT = dirname(DJANGO_PROJECT_CONFIG)

# Site name:
SITE_NAME = basename(SITE_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(SITE_ROOT)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
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
    'storages',

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
    # 'cached_auth.Middleware',
    'django_auth_lti.middleware.LTIAuthMiddleware',
    ## from new version of icommons django-auth-lti
    # 'django_auth_lti.middleware_patched.MultiLTILaunchAuthMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django_auth_lti.backends.LTIAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
)

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS':[
        normpath(join(SITE_ROOT, 'templates')),
    ],
    'OPTIONS':{
        'context_processors': [
            # django auth
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.request',  # adds `request` object to templates context
            # 'django.template.context_processors.debug',

            # enable django messages
            'django.contrib.messages.context_processors.messages',
        ],
        'loaders': [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ],
        'debug':True,
    },
},]

LOGIN_URL = reverse_lazy('lti_auth_error')

ROOT_URLCONF = 'adaptive_edx.urls'

WSGI_APPLICATION = 'adaptive_edx.wsgi.application'


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    normpath(join(SITE_ROOT, 'static')),
)

STATIC_URL = '/static/'
STATIC_ROOT = secure.STATIC_ROOT

#### django-bootstrap ####
BOOTSTRAP3 = {
    'include_jquery': True,
}

# allow post requests from edx
CORS_ORIGIN_ALLOW_ALL = True

LTI_OAUTH_CREDENTIALS = secure.LTI_OAUTH_CREDENTIALS

## for dce version of django-auth-lti
from oauthlib.oauth1 import RequestValidator
LTI_REQUEST_VALIDATOR = 'bridge_lti.validator.LTIRequestValidator'

# base url for rendering xblocks from edx
EDX_BASE_URL = 'https://courses.edx.org/xblock/'

# tutorgen related
TUTORGEN_URL_BASE = secure.TUTORGEN_URL_BASE
TUTORGEN_USER = secure.TUTORGEN_USER
TUTORGEN_PASS = secure.TUTORGEN_PASS
TUTORGEN_COURSE_ID = secure.TUTORGEN_COURSE_ID

# switch for activity service
ACTIVITY_SERVICE = secure.ACTIVITY_SERVICE[os.environ.get('ENV_TYPE', 'mock')]

AUTH_USER_MODEL = 'bridge_lti.BridgeUser'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'module:collection-list'
ALLOWED_HOSTS = secure.ALLOWED_HOSTS

DATABASES = secure.DATABASES
