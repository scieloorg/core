from rest_framework.exceptions import ValidationError

from django.db.models import Q
from rest_framework import viewsets

from article import models
from core.validators import validate_params
from .serializers import IssueSerializer


class GenericIssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    http_method_names = ["get"]
    queryset = models.Issue.objects.all()


class IssueViewSet(GenericIssueViewSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        collection = self.request.query_params.get("collection")
        from_date = self.request.query_params.get("from_date")
        until_date = self.request.query_params.get("until_date")
        if not collection:
            raise ValidationError("Collection is a required query parameter")

        validate_params(self.request, "collection", "from_date", "until_date")

        params = {}
        if collection:
            params["journal__scielojournal__collection__acron3"] = collection
        if from_date:
            params["created__gte"] = from_date.replace("/", "-")
        if until_date:
            params["created__lte"] = until_date.replace("/", "-")

        if params:
            queryset = queryset.filter(**params)
        return queryset 

    