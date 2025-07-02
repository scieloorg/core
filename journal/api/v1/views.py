from rest_framework import serializers, viewsets
from django.db.models import F

from core.utils.utils import formated_date_api_params
from core.validators import validate_params
from journal import models

from .serializers import JournalSerializer


class ArticleMetaFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Journal

    def to_representation(self, instance):
        collection = getattr(instance, 'collection_acron', None)
        return instance.articlemeta_format(collection)

    
class GenericJournalViewSet(viewsets.ModelViewSet):
    serializer_class = JournalSerializer
    http_method_names = ["get"]
    queryset = models.Journal.objects.all()


class JournalViewSet(GenericJournalViewSet):
    def get_queryset(self):
        query_params = self.request.query_params
        
        validate_params(
            self.request,
            "issn_print",
            "issn_electronic",
            "issn",
            "title",
            "thematic_areas",
            "toc_item",
            "page",
            "collection",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",
            "formats",
            "issnl",
            "",
        )

        params = {}
        if issn := query_params.get("issn"):
           params["scielojournal__issn_scielo"] = issn
        if issn_electronic := query_params.get("issn_electronic"):
           params["official__issn_electronic"] = issn_electronic
        if issn_print := query_params.get("issn_print"):
           params["official__issn_print"] = issn_print
        if issnl := query_params.get("issnl"):
           params["official__issnl"] = issnl
        if title := query_params.get("title"):
           params["title"] = title
        if toc_item := query_params.get("toc_item"):
           params["journaltocsection__toc_items__text"] = toc_item
        if thematic_areas := query_params.get("thematic_areas"):
           params["subject__value__in"] = thematic_areas.split(",")
        if collection_acron := query_params.get("collection"):
           params["scielojournal__collection__acron3"] = collection_acron
        
        formated_date = formated_date_api_params(query_params)
        if formated_date:
            params.update(formated_date)

        query = super().get_queryset()
        if query_params.get("formats") == "articlemeta":
            return query.filter(
                scielojournal__journal__isnull=False
            ).filter(**params).annotate(
                collection_acron=F('scielojournal__collection__acron3')
            ).order_by('created').distinct()
        
        return query.filter(**params).order_by('created').distinct()

    def get_serializer_class(self):
        format_param = self.request.query_params.get("formats")
        if format_param == "articlemeta":
            return ArticleMetaFormatSerializer
        return JournalSerializer