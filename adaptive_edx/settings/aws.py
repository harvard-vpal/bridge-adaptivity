from .base import *
import secure

# Need to set AWS_ENV_TYPE as environment variable in AWS console, e.g. 'production', 'development' or 'test'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True

#### AMAZON S3 STATICFILES STORAGE ####
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
AWS_STORAGE_BUCKET_NAME = secure.AWS_STORAGE_BUCKET_NAME
AWS_S3_ACCESS_KEY_ID = secure.AWS_S3_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = secure.AWS_SECRET_ACCESS_KEY

# Database
DATABASES = {
    'default': secure.AWS_DATABASE
}


# INSTALLED_APPS += ('debug_toolbar', )
# MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
# def show_toolbar(request):
#     return True
# DEBUG_TOOLBAR_CONFIG = {
#     "SHOW_TOOLBAR_CALLBACK" : show_toolbar,
#     'INTERCEPT_REDIRECTS': True,
# }
