from django.db.models import Q
from rest_framework import viewsets

from journal import models
from .serializers import JournalSerializer

from core.validators import validate_params
from core.utils.utils import params_api


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
        toc_item = self.request.query_params.get("toc_item")
        from_date_created = self.request.query_params.get("from_date_created")
        until_date_created = self.request.query_params.get("until_date_created")
        from_date_updated = self.request.query_params.get("from_date_updated")
        until_date_updated = self.request.query_params.get("until_date_updated")
        
        # funcao para permitir apenas estes paramentros
        validate_params(
            self.request, 
            "issn_print", 
            "issn_electronic", 
            "issnl", 
            "title", 
            "thematic_areas", 
            "toc_item",
            "page",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",
            "",
        )

        queryset = super().get_queryset()

        params = params_api(
            scielojournal__issn_scielo=issn,
            official__issn_electronic= issn_electronic,
            official__issn_print=issn_print,
            official__issnl=issnl,
            title=title,
            journaltocsection__toc_items__text=toc_item,
            subject__value__in=thematic_areas.split(",") if thematic_areas else None,
            created__gte=from_date_created.replace("/", "-") if from_date_created else None,
            created__lte=until_date_created.replace("/", "-") if until_date_created else None,
            updated__gte=from_date_updated.replace("/", "-") if from_date_updated else None,
            updated__lte=until_date_updated.replace("/", "-") if until_date_updated else None
        )

        return queryset.filter(**params)
