from django.conf import settings
from django.conf.urls import url, include
from rest_framework import routers

from api.views import sources, ActivityViewSet, CollectionViewSet

router = routers.DefaultRouter(trailing_slash=True)
router.register('activity', ActivityViewSet)
router.register('collection', CollectionViewSet)


urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^sources/$', sources, name='sources'),
]

# Add rest API dashboard in DEBUG mode
if settings.DEBUG:
    urlpatterns.append(url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')))
