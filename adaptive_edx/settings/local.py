from .base import *
import secure

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS += ('debug_toolbar', 'sslserver')

MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = normpath(join(SITE_ROOT, 'http_static'))

# For Django Debug Toolbar:
INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)

DEBUG_TOOLBAR_CONFIG = {
   'INTERCEPT_REDIRECTS': False,
}

# LOGGING = {
#    'version': 1,
#    'disable_existing_loggers': True,
#    'formatters': {
#        'verbose': {
#            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
#        },
#        'simple': {
#            'format': '%(levelname)s %(module)s %(message)s'
#        }
#    },
#    'filters': {
#        'require_debug_false': {
#            '()': 'django.utils.log.RequireDebugFalse'
#        }
#    },
#    'handlers': {
#        'mail_admins': {
#            'level': 'ERROR',
#            'filters': ['require_debug_false'],
#            'class': 'django.utils.log.AdminEmailHandler',
#        },
#        # Log to a text file that can be rotated by logrotate
#        'logfile': {
#            'level': 'DEBUG',
#            'class': 'logging.handlers.WatchedFileHandler',
#            'filename': 'app.log',
#            'formatter': 'verbose',
#        },
#        'console': {
#            'level': 'DEBUG',
#            'class': 'logging.StreamHandler',
#            'formatter': 'simple',
#        },
#        'request': {
#            'level': 'DEBUG',
#            'class': 'logging.handlers.WatchedFileHandler',
#            'filename': 'request.log',
#            'formatter': 'verbose',
#        },
#     },

#    'loggers': {
#        'django.request': {
#            'handlers': ['request'],
#            'level': 'DEBUG',
#            'propagate': False,
#        },
#        'django': {
#            'handlers': ['console', 'logfile'],
#            'level': 'DEBUG',
#            'propagate': True,
#        },
#        'django_auth_lti': {
#            'handlers': ['console', 'logfile'],
#            'level': 'DEBUG',
#            'propagate': True,
#        },
#        'oauth2': {
#            'handlers': ['console', 'logfile'],
#            'level': 'DEBUG',
#            'propagate': True,
#        },
#        'ims_lti_py': {
#            'handlers': ['console', 'logfile'],
#            'level': 'DEBUG',
#            'propagate': True,
#        },
#    }
# }




