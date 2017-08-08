from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from .views import CollectionList, CollectionCreate

urlpatterns = [
    url(r'^collection/$', login_required(CollectionList.as_view()), name='collection-list'),
    url(r'^collection/add/$', CollectionCreate.as_view(), name='collection-add'),
]
