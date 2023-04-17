# urls.py
from django.conf.urls import include, re_path
from rest_framework.routers import DefaultRouter

from .views import PidProviderViewSet

router = DefaultRouter()
router.register("pid_provider", PidProviderViewSet, basename="pid_provider")


app_name = "pid_provider"
urlpatterns = [
    re_path("^", include(router.urls)),
    re_path(r"^pid_provider/(?P<filename>[^/]+)$", PidProviderViewSet),
]
