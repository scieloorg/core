from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from article.api.v1.views import ArticleViewSet

from issue.api.v1.views import IssueViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()


router.register("article", ArticleViewSet, basename="Article")
router.register("issue", IssueViewSet, basename="Issue")

app_name = "api"
urlpatterns = router.urls
