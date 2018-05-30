from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import RedirectView

from api.urls import urlpatterns as api
from bridge_lti.urls import urlpatterns as lti
from module.urls import urlpatterns as module
from . import views


urlpatterns = [
    path('login/', auth_views.login, name='login'),
    path('logout/', auth_views.logout, name='logout'),
    path('admin/', admin.site.urls),
    path('health/', views.health),

    path('', login_required(RedirectView.as_view(pattern_name='module:collection-list')), name='index'),
    path('lti/', include(lti)),
    path('module/', include(module)),
    path('api/', include(api)),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path(r'__debug__/', include(debug_toolbar.urls)), ] + urlpatterns
