from django.conf.urls import url
from . import views

urlpatterns = [

    url(r'^launch$', views.launch, name='launch'),

]