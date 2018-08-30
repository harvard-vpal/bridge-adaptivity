import hashlib

from django.conf import settings
from django.shortcuts import render
import shortuuid


def short_token():
    """Generate a hash that can be used as lti consumer key."""
    hash = hashlib.sha1(shortuuid.uuid().encode('utf-8'))
    hash.update(settings.SECRET_KEY.encode('utf-8'))
    return hash.hexdigest()[::2]


def stub_page(request, title='announcement', message='coming soon!', tip='this adaptivity sequence is about to start.'):
    """
    Render stub page, announcement page is default.
    """
    return render(
        request,
        template_name="bridge_lti/announcement.html",
        context={
            'title': title,
            'message': message,
            'tip': tip,
        }
    )
