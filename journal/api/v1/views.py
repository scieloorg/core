from django.db.models import Q
from rest_framework import viewsets, serializers
from rest_framework.response import Response

from journal import models
from .serializers import JournalSerializer

from core.validators import validate_params

class ArticleMetaFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Journal

    def to_representation(self, instance):
        return instance.articlemeta_format()

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
            "formats",
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
        if toc_item:
            params['journaltocsection__toc_items__text'] = toc_item    
        if thematic_areas:
            params['subject__value__in'] = thematic_areas.split(",")
        if from_date_created:
            params["created__gte"] = from_date_created.replace("/", "-")
        if until_date_created:
            params["created__lte"] = until_date_created.replace("/", "-")
        if from_date_updated:
            params["updated__gte"] = from_date_updated.replace("/", "-")
        if until_date_updated:
            params["updated__lte"] = until_date_updated.replace("/", "-")

        return queryset.filter(**params)
    
    def get_serializer_class(self):
        format_param = self.request.query_params.get("formats")
        if format_param == "articlemeta":
            return ArticleMetaFormatSerializer
        return JournalSerializer
