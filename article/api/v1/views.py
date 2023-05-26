from rest_framework import viewsets

from article import models

from .serializers import ArticleSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    http_method_names = ["get"]
    queryset = models.Article.objects.all()

    # def get_queryset(self):
    #     """
    #     This view should return a list of all published Education.
    #     """
    #     # user = self.request.user

    #     return models.Article.objects.all()
