from django.urls import path

from . import views

urlpatterns = [
    path('', views.get_mattermost_news),
    path('<identifier>', views.get_news),
]
