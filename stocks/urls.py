from django.urls import path

from . import views

urlpatterns = [
    path('graph/<identifier>/', views.graph_GET, name='graph_GET'),
    path('graph/<identifier>/<span>/', views.graph_GET, name='graph_GET'),
    path('graph', views.graph_POST, name='graph_POST'),
    path('graph/image/<img_name>.png', views.graph_img, name='graph_img'),
    path('option/<identifier>/<price_str>/<expiration>/', views.option_graph_GET, name='option_graph_GET'),
    path('option/<identifier>/<price_str>/<expiration>/<span>/', views.option_graph_GET, name='option_graph_GET'),
    path('option/graph', views.option_graph_POST, name='graph_POST'),
    path('option/graph/image/<img_name>.png', views.option_graph_img, name='option_graph_img'),
    path('info', views.info_POST, name='info_POST'),
    path('info/<symbol>/', views.info_GET, name='info_GET')
]
