# channels routing.py
from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/sequence/(?P<sequence_item>[^/]+)/$', consumers.CallbackSequenceConsumer),
]
