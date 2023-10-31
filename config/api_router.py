from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from article.api.v1.views import ArticleViewSet
from issue.api.v1.views import IssueViewSet
from pid_provider.api.v1.views import PidProviderViewSet
from journal.api.v1.views import JournalViewSet, JournalIdentifierViewSet

app_name = "pid_provider"

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("article", ArticleViewSet, basename="article")
router.register("issue", IssueViewSet, basename="issue")
router.register("pid_provider", PidProviderViewSet, basename="pid_provider")
router.register("journal/identifiers", JournalIdentifierViewSet, basename='journal_identifiers')
router.register("journal", JournalViewSet, basename="journal_detail")

urlpatterns = router.urls
