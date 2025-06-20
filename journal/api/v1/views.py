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
        query_params = self.request.query_params
        
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
            "collection_acron",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",
            "issnl",
            "",
        )

        queryset = super().get_queryset()

        if issn := query_params.get("issn"):
           queryset = queryset.filter(scielojournal__issn_scielo=issn)
        if issn_electronic := query_params.get("issn_electronic"):
            queryset = queryset.filter(official__issn_electronic=issn_electronic)
        if issn_print := query_params.get("issn_print"):
            queryset = queryset.filter(official__issn_print=issn_print)
        if issnl := query_params.get("issnl"):
            queryset = queryset.filter(official__issnl=issnl)
        if title := query_params.get("title"):
            queryset = queryset.filter(title=title)
        if toc_item := query_params.get("toc_item"):
            queryset = queryset.filter(journaltocsection__toc_items__text=toc_item)
        if thematic_areas := query_params.get("thematic_areas"):
            queryset = queryset.filter(subject__value__in=thematic_areas.split(","))
        if collection_acron := query_params.get("collection"):
            queryset = queryset.filter(scielojournal__collection__acron3=collection_acron)

        for date_param, filter_key in [
            ("from_date_created", "created__gte"),
            ("until_date_created", "created__lte"),
            ("from_date_updated", "updated__gte"),
            ("until_date_updated", "updated__lte"),
        ]:
            if data_value := query_params.get(date_param):
                try:
                    formated_date = data_value.replace("/", "-")
                    queryset = queryset.filter(**{filter_key: formated_date})
                except (ValueError, AttributeError):
                    continue

        return queryset
