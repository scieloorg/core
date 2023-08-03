from rest_framework import serializers, viewsets

from article import models

from .serializers import IssueSerializer


class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    http_method_names = ["get"]
    queryset = models.Issue.objects.all()
