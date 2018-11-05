import hashlib

from django.conf import settings
import shortuuid


def short_token():
    """Generate a hash that can be used as lti consumer key."""
    hash = hashlib.sha1(shortuuid.uuid().encode('utf-8'))
    hash.update(settings.SECRET_KEY.encode('utf-8'))
    return hash.hexdigest()[::2]
