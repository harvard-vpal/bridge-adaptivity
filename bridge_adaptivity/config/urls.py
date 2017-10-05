from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from . import views


urlpatterns = [
    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, name='logout'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^health/$', views.health),

    url(r'^$', login_required(RedirectView.as_view(pattern_name='module:collection-list')), name='index'),
    url(r'^lti/', include('bridge_lti.urls', namespace="lti")),
    url(r'^module/', include('module.urls', namespace="module")),
    url(r'^api/', include('api.urls', namespace="api")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r'^__debug__/', include(debug_toolbar.urls)), ] + urlpatterns
