"""
Example of secret module with secure settings.

Should be ignored by VCS (Git).
"""

# Standard Django secret key (can be generated via http://www.miniwebtool.com/django-secret-key-generator/)
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = 'xf!mz_(en(p=tcp$-4%lse$9f55e+q)10rcve@bxhzcnrtv)hj-key'
STATIC_ROOT = 'static/'
ALLOWED_HOSTS = []  # add bridge host in production
BRIDGE_HOST = 'localhost:8008'

# related to `bridge_adaptivity/envs/pg.env`
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bridge_db',
        'USER': 'bridge',
        'PASSWORD': 'bridge-adaptivity',
        'HOST': 'postgres',
        'PORT': 5432,
    }
}

# Comment Engine's parameters to use default Mock Adaptive Engine
# ENGINE_MODULE = 'module.engines.engine_vpal'
# ENGINE_DRIVER = 'EngineVPAL'
# ENGINE_SETTINGS = {
#     'HOST': 'https://example.com',
#     'TOKEN': 'very_secure_token',
# }
