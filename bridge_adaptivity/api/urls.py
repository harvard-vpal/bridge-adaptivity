from django.conf.urls import url

from api.views import sources

urlpatterns = [
    url(r'^sources/$', sources, name='sources'),
]
