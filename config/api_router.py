from os.path import basename
from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from pid_provider.api.views import PidProviderViewSet

app_name = "pid_provider"

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("pid_provider", PidProviderViewSet, basename="pid_provider")

urlpatterns = router.urls
