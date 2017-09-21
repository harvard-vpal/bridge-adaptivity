import hashlib

from django.conf import settings
import shortuuid


def short_token():
    """Generate a hash that can be used as lti consumer key."""
    hash = hashlib.sha1(shortuuid.uuid())
    hash.update(settings.SECRET_KEY)
    return hash.hexdigest()[::2]
