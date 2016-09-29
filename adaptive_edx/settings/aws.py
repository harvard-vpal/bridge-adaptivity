import os
os.environ.setdefault('ENV_TYPE', 'aws')
from .base import *
import secure

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
