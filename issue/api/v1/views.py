from rest_framework import viewsets

from issue import models
from .serializers import IssueSerializer
from core.utils.validators import validate_params


class GerenicIssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    http_method_names = ["get"]
    queryset = models.Issue.objects.all()


class IssueViewSet(GerenicIssueViewSet):
    def get_queryset(self):
        collection = self.request.query_params.get("collection")
        from_date = self.request.query_params.get("from_date")
        until_date = self.request.query_params.get("until_date")

        validate_params(self.request, "collection", "from_date", "until_date")
        queryset = super().get_queryset()

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
