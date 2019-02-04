from django.conf import settings
from django.conf.urls import include, url
from django.urls import path
from rest_framework import routers

from api.views import ActivityViewSet, CollectionViewSet, sources, sync_collection

router = routers.DefaultRouter(trailing_slash=True)
router.register('activity', ActivityViewSet, base_name='activity')
router.register('collection', CollectionViewSet, base_name='collection')

urls_list = [
    url(r'^', include(router.urls)),
    url(r'^sources/$', sources, name='sources'),
    path('collection/<slug:slug>/sync/', sync_collection, name='sync_collection')
]

# Add rest API dashboard in DEBUG mode
if settings.DEBUG:
    urls_list.append(url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')))

urlpatterns = (urls_list, 'api')
