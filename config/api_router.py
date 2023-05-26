from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from article.api.v1.views import ArticleViewSet


if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()


router.register("article", ArticleViewSet, basename="Article")

app_name = "api"
urlpatterns = router.urls