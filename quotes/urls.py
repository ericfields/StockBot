from django.urls import path

from . import views

urlpatterns = [
    path('', views.get_mattermost_chart),
    path('all', views.get_mattermost_chart_for_all),
    path('update/', views.update_mattermost_chart, name='quote_update'),
    path('image/<img_name>.png', views.get_chart_img, name='quote_img'),
    path('info', views.stock_info),

    path('view/<identifiers>', views.get_chart),
    path('view/<identifiers>/<span>', views.get_chart),
]
