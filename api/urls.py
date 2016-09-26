from django.conf.urls import include, url
# from django.contrib import admin

from . import views


urlpatterns = [
	url(r'^problem_attempt$', views.problem_attempt, name='problem_attempt'),
]

