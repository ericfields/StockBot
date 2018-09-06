from django.urls import path

from . import views

urlpatterns = [
    path('graph', views.graph_POST, name='graph_POST'),
    path('graph/<symbol>', views.graph_GET, name='graph_GET'),
    path('graph/image/<img_name>.png', views.graph_img, name='graph_img'),
    path('info', views.info_POST, name='info_POST'),
    path('info/<symbol>', views.info_GET, name='info_GET')
]
