from unittest.mock import patch
from article.models import Article


class ArticleTestMixin:
    """Mixin com helpers e mocks para o app Article."""

    def make_article(self, user=None, pid_v3=None):
        kwargs = {}
        if user:
            kwargs["creator"] = user
        if pid_v3:
            kwargs["pid_v3"] = pid_v3
        return Article.objects.create(**kwargs)
