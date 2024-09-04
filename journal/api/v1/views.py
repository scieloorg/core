from django.db.models import Q
from rest_framework import viewsets

from journal import models
from .serializers import JournalSerializer

from core.validators import validate_params



class GenericJournalViewSet(viewsets.ModelViewSet):
    serializer_class = JournalSerializer
    http_method_names = ["get"]
    queryset = models.Journal.objects.all()


class JournalViewSet(GenericJournalViewSet):
    def get_queryset(self):
        issn = self.request.query_params.get("issn")
        title = self.request.query_params.get("title")
        issn_print = self.request.query_params.get("issn_print")
        issn_electronic = self.request.query_params.get("issn_electronic")
        issnl = self.request.query_params.get("issnl")
        thematic_areas = self.request.query_params.get("thematic_areas")

        # funcao para permitir apenas estes paramentros
        validate_params(
            self.request, 
            "issn_print", 
            "issn_electronic", 
            "issnl", 
            "title", 
            "thematic_areas", 
            "page",
            "",
        )

        queryset = super().get_queryset()

        params = {}
        if issn:
            params['scielojournal__issn_scielo'] = issn
        if issn_electronic:
            params['official__issn_electronic'] = issn_electronic
        if issn_print:
            params['official__issn_print'] = issn_print
        if issnl:
            params['official__issnl'] = issnl
        if title:
            params['title'] = title
        if thematic_areas:
            params['subject__value__in'] = thematic_areas.split(",")

        return queryset.filter(**params)
