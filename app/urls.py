from django.contrib import admin
from django.urls import path, include

from django.urls import path


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/user/", include("user.urls")),
    path("api/spread/", include("spread.urls")),
    path("sentry-debug/", trigger_error),
]
