from rest_framework import viewsets

from article import models

from .serializers import ArticleSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    http_method_names = ["get"]
    queryset = models.Article.objects.all()

    def get_queryset(self):
        queryset = models.Article.objects.all()
        doi_prefix = self.request.query_params.get("doi_prefix", None)
        if doi_prefix is not None:
            queryset = queryset.filter(doi__value__startswith=doi_prefix)
        return queryset
