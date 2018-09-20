from django.urls import path

from . import views
from . import quote_views

urlpatterns = [
    path('quotes/<identifiers>/', quote_views.get_graph),
    path('quotes', quote_views.get_mattermost_graph),
    path('quotes/image/<img_name>.png', quote_views.get_graph_img),
    path('portfolios/', views.portfolios),
    path('graph/<identifier>/', views.stock_graph_GET),
    path('graph/<identifier>/<span>/', views.stock_graph_GET),
    path('graph', views.stock_graph_POST),
    path('graph/image/<img_name>.png', views.stock_graph_img),
    path('option/graph/<identifier>/', views.option_graph_GET),
    path('option/graph/<identifier>/<span>/', views.option_graph_GET),
    path('option/graph', views.option_graph_POST),
    path('option/graph/image/<img_name>.png', views.option_graph_img),
    path('info/<symbol>/', views.stock_info_POST),
]
