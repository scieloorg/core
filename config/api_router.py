from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from article.api.v1.views import ArticleViewSet
from issue.api.v1.views import IssueViewSet
from pid_provider.api.v1.views import PidProviderViewSet, FixPidV2ViewSet
from journal.api.v1.views import JournalViewSet, GenericJournalViewSet


app_name = "pid_provider"

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("article", ArticleViewSet, basename="Article")
router.register("issue", IssueViewSet, basename="Issue")
router.register("pid_provider", PidProviderViewSet, basename="pid_provider")
router.register("fix_pid_v2", FixPidV2ViewSet, basename="fix_pid_v2")
router.register("journal", JournalViewSet, basename="journal")



urlpatterns = router.urls
