from django.urls import path

from . import views
from . import portfolio_views

urlpatterns = [
    path('quotes/<identifiers>/', views.get_graph),
    path('quotes', views.get_mattermost_graph),
    path('quotes/image/<img_name>.png', views.get_graph_img),
    path('info', views.stock_info),
    path('portfolios/', portfolio_views.portfolios),
]
