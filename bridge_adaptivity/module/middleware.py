from django.contrib.sites.shortcuts import get_current_site


class BridgeSameSiteMiddleware:
    """
    Middleware to add a `SameSite=None` attribute to the session cookie for
    `deposit/webapp` responses. This is a work-around in-place of
    :class:`django.http.HttpResponse.set_cookie`, which does not
    allow `samesite` values of ``None``.
    Polaris developers MUST add this class to their Django app's
    ``settings.MIDDLEWARE``. Specifically, the class must be listed
    `above` :class:`django.contrib.sessions.middleware.SessionMiddleware`,
    like so:
    ::
        MIDDLEWARE = [
            'module.middleware.BridgeSameSiteMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ]
    Fix: https://github.com/django/django/pull/11894
    Boilerplate code from:
    https://docs.djangoproject.com/en/2.2/topics/http/middleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        from django.conf import settings

        request_domain = get_current_site(request).domain

        if settings.SESSION_COOKIE_NAME in response.cookies and not request_domain.startswith('localhost'):
            response.cookies[settings.SESSION_COOKIE_NAME]["samesite"] = "None"
            response.cookies[settings.SESSION_COOKIE_NAME]["secure"] = True
        return response


import_path = "module.middleware.BridgeSameSiteMiddleware"
