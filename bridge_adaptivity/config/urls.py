from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView

from bridge_lti.urls import urlpatterns as lti
from module.urls import urlpatterns as module
from api.urls import urlpatterns as api

from . import views


urlpatterns = [
    path(r'^login/$', auth_views.login, name='login'),
    path(r'^logout/$', auth_views.logout, name='logout'),
    path(r'^admin/', admin.site.urls),
    path(r'^health/$', views.health),

    path(r'^$', login_required(RedirectView.as_view(pattern_name='module:collection-list')), name='index'),
    path(r'^lti/', include(lti)),
    path(r'^module/', include(module)),
    path(r'^api/', include(api)),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path(r'^__debug__/', include(debug_toolbar.urls)), ] + urlpatterns
