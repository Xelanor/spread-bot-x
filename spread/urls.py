from django.urls import path, include

from spread import views

urlpatterns = [
    path("", views.spread_bots_data, name="spread_bots_data"),
    path("add-new-bot", views.add_spread_bot, name="add_spread_bot"),
    path("historical", views.spread_historical_data, name="spread_historical_data"),
    path("transactions", views.get_spread_transactions, name="get_spread_transactions"),
    path("average-correction", views.average_correction, name="average_correction"),
    path("budget-update", views.budget_update, name="budget_update"),
]
