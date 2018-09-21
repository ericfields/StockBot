from django.urls import path

from . import views
from . import portfolio_views

urlpatterns = [
    path('quotes/<identifiers>/', views.get_chart),
    path('quotes', views.get_mattermost_chart),
    path('quote_update/', views.update_mattermost_chart, name='quote_update'),
    path('quotes/image/<img_name>.png', views.get_chart_img, name='quote_img'),
    path('info', views.stock_info),
    path('portfolios/', portfolio_views.portfolios),
]
