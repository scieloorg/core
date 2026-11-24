from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from issue.api.v2.views import IssueViewSet

# Roteador da API v2, montado em /api/v2/ sem prefixo de idioma (ver config/urls.py)
app_name = "api_v2"

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("issue", IssueViewSet, basename="Issue")

urlpatterns = router.urls
