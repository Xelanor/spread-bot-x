from django.urls import path, include

from spread import views

urlpatterns = [path("", views.spread_bots_data, name="spread_bots_data")]
