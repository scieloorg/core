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
        from_publication_date = self.request.query_params.get("from_publication_date")
        until_publication_date = self.request.query_params.get("until_publication_date")
        issn_print = self.request.query_params.get("issn_print")
        issn_electronic = self.request.query_params.get("issn_electronic")
        volume = self.request.query_params.get("volume")
        number = self.request.query_params.get("number")
        supplement = self.request.query_params.get("supplement")
        
        validate_params(
            self.request, 
            "collection", 
            "from_date",
            "until_date",
            "from_publication_year",
            "until_publication_year",
            "issn_print",
            "issn_electronic",  
            "volume", 
            "number",
            "supplement",
            "page",
        )

        params = {}
        if collection:
            params["journal__scielojournal__collection__acron3"] = collection
        if from_date:
            params["created__gte"] = from_date.replace("/", "-")
        if until_date:
            params["created__lte"] = until_date.replace("/", "-")
        if from_publication_date:
            params["year__gte"] = from_date.replace("/", "-")
        if until_publication_date:
            params["year__lte"] = until_date.replace("/", "-")
        if issn_print:
            params["journal__official__issn_print"] = issn_print
        if issn_electronic:
            params["journal__official__issn_electronic"] = issn_electronic
        if volume:
            params["volume"] = volume
        if number:
            params["number"] = number                
        if supplement:
            params["supplement"] = supplement
        if params:
            queryset = queryset.filter(**params)
        return queryset 

    