from rest_framework import viewsets

from journal import models
from .serializers import JournalSerializer
from core.core.utils.validators import validate_issn, validate_params


class GenericJournalViewSet(viewsets.ModelViewSet):
    serializer_class = JournalSerializer
    http_method_names = ["get"]
    queryset = models.Journal.objects.all()


class JournalViewSet(GenericJournalViewSet):
    def get_queryset(self):
        issn = self.request.query_params.get("issn")
        collection = self.request.query_params.get("collection")
        
        validate_issn(issn)
        validate_params(self.request, "collection", "issn")
        
        queryset = super().get_queryset()

        params = {}

        if collection:
            params['scielojournal__collection__acron3'] = collection
        params['scielojournal__issn_scielo'] = issn

        queryset = queryset.filter(**params)
        if not queryset:
            return queryset.none()
        return queryset
    

class JournalIdentifierViewSet(GenericJournalViewSet):
    def get_queryset(self):
        collection = self.request.query_params.get("collection")
        from_date = self.request.query_params.get("from_date")
        until_date = self.request.query_params.get("until_date")
        
        validate_params(self.request, "collection", "from_date", "until_date")
        queryset = super().get_queryset()

        params = {}

        if collection:
            params['scielojournal__collection__acron3'] = collection
        if from_date:
            params['created__gte'] = from_date.replace("/", "-")
        if until_date:
            params['created__lte'] = until_date.replace("/", "-")

        if params:
            queryset = queryset.filter(**params)
        return queryset
        
