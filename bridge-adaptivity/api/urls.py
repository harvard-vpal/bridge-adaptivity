from django.conf.urls import url

from api.views import get_sources

urlpatterns = [
    url(r'^sources/$', get_sources, name='sources'),
]
