from django.db.models import Q
from rest_framework import viewsets

from journal import models
from .serializers import JournalSerializer
from journal.validators import validate_issn, validate_params


class GenericJournalViewSet(viewsets.ModelViewSet):
    serializer_class = JournalSerializer
    http_method_names = ["get"]
    queryset = models.Journal.objects.all()


class JournalViewSet(GenericJournalViewSet):
    def get_queryset(self):
        issn = self.request.query_params.get("issn")
        validate_issn(issn)
        validate_params(self.request, "issn")

        queryset = super().get_queryset()

        params = {}
        params['scielojournal__issn_scielo'] = issn
        params['official__issn_electronic'] = issn
        params['official__issn_print'] = issn
        params['official__issnl'] = issn

        query = Q(scielojournal__issn_scielo=issn) | \
                Q(official__issn_electronic=issn) | \
                Q(official__issn_print=issn) | \
                Q(official__issnl=issn)
    
        queryset = queryset.filter(query)
        return queryset if queryset.exists() else queryset.none()