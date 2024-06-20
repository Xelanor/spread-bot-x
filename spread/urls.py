from django.urls import path, include

from spread import views

urlpatterns = [
    path("", views.spread_bots_data, name="spread_bots_data"),
    path("transactions", views.get_spread_transactions, name="get_spread_transactions"),
]
