from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from . import views

urlpatterns = [
	
    url(r'^$', views.home, name='home'),
    url(r'^auth_error/', views.lti_auth_error, name='lti_auth_error'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^lti/', include('bridge_lti.urls', namespace="lti")),
    url(r'^module/', include('module.urls', namespace="module")),
    url(r'^api/', include('api.urls', namespace="api")),
    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r'^__debug__/', include(debug_toolbar.urls)), ] + urlpatterns
