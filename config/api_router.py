from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from article.api.v1.views import ArticleViewSet
from issue.api.v1.views import IssueViewSet
from pid_provider.api.v1.views import PidProviderViewSet

app_name = "pid_provider"

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("article", ArticleViewSet, basename="Article")
router.register("issue", IssueViewSet, basename="Issue")
router.register("pid_provider", PidProviderViewSet, basename="pid_provider")

urlpatterns = router.urls
