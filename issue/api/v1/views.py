from django.db.models import Q
from rest_framework import serializers, viewsets

from article import models
from core.utils.utils import formated_date_api_params
from core.validators import validate_params

from .serializers import IssueSerializer


class ArticleMetaFormatIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Issue
    
    def to_representation(self, instance):
        return instance.articlemeta_format


class GenericIssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    http_method_names = ["get"]
    queryset = models.Issue.objects.all()


class IssueViewSet(GenericIssueViewSet):
    def get_queryset(self):
        """
        from_publication_date e until_publication_date:
            parâmetros que recuperam registros baseados no ano de publicação do periódico.

        from_date e until_date:
            parâmetros que recuperam registros a partir da data de atualização do periódico. 
            Importante para recuperar registros mais recentes.
        """
        query_params = self.request.query_params
        
        validate_params(
            self.request, 
            "collection",
            "from_publication_year",
            "until_publication_year",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",
            "issn_print",
            "issn_electronic",
            "issn",
            "volume", 
            "number",
            "supplement",
            "page",
            "formats",
            "",
        )
        queryset = super().get_queryset()

        if collection := query_params.get("collection"):
            queryset = queryset.filter(journal__scielojournal__collection__acron3=collection)
        if from_publication_year := query_params.get("from_publication_year"):
            queryset = queryset.filter(year__gte=from_publication_year)
        if until_publication_year := query_params.get("until_publication_year"):
            queryset = queryset.filter(year__lte=until_publication_year)
        if issn_print := query_params.get("issn_print"):
            queryset = queryset.filter(journal__official__issn_print=issn_print)
        if issn_electronic := query_params.get("issn_electronic"):
            queryset = queryset.filter(journal__official__issn_electronic=issn_electronic)
        if volume := query_params.get("volume"):
            queryset = queryset.filter(volume=volume)
        if number := query_params.get("number"):
            queryset = queryset.filter(number=number)
        if supplement := query_params.get("supplement"):
            queryset = queryset.filter(supplement=supplement)
        if issn := query_params.get("issn"):
            queryset = queryset.filter(Q(journal__official__issn_print=issn) | Q(journal__official__issn_electronic=issn))

        dates = formated_date_api_params(query_params)
        queryset = queryset.filter(**dates)


        return queryset 

    def get_serializer_class(self):
        format_param = self.request.query_params.get("formats")
        if format_param == "articlemeta":
            return ArticleMetaFormatIssueSerializer
        return IssueSerializer