from django.conf.urls import url, include
from . import views

urlpatterns = [
	url(r'^launch/(?P<user_module_id>[0-9]+)$', views.launch, name='launch'),
    url(r'^(?P<user_module_id>[0-9]+)/(?P<position>[0-9]+)$', views.sequence_item, name='sequence_item'),
	url(r'^(?P<user_module_id>[0-9]+)/(?P<position>[0-9]+)/next_activity$', views.next_activity, name='next_activity'),
	url(r'^sequence_complete/(?P<user_module_id>[0-9]+)$', views.sequence_complete, name='sequence_complete'),
	url(r'^completion_message$', views.completion_message, name='completion_message'),
]

