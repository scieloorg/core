from article import models
from .serializers import IssueSerializer

from rest_framework import viewsets, serializers


class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    http_method_names = ["get"]
    queryset = models.Issue.objects.all()
