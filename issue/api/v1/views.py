from rest_framework.exceptions import ValidationError

from django.db.models import Q
from rest_framework import viewsets, serializers

from article import models
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
        queryset = super().get_queryset()
        collection = self.request.query_params.get("collection")
        from_publication_year = self.request.query_params.get("from_publication_year")
        until_publication_year = self.request.query_params.get("until_publication_year")
        from_date_created = self.request.query_params.get("from_date_created")
        until_date_created = self.request.query_params.get("until_date_created")
        from_date_updated = self.request.query_params.get("from_date_updated")
        until_date_updated = self.request.query_params.get("until_date_updated")
        issn_print = self.request.query_params.get("issn_print")
        issn_electronic = self.request.query_params.get("issn_electronic")
        volume = self.request.query_params.get("volume")
        number = self.request.query_params.get("number")
        supplement = self.request.query_params.get("supplement")
        
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
            "volume", 
            "number",
            "supplement",
            "page",
            "formats",
            "",
        )

        params = {}
        if collection:
            params["journal__scielojournal__collection__acron3"] = collection
        if from_publication_year:
            params["year__gte"] = from_publication_year
        if until_publication_year:
            params["year__lte"] = until_publication_year
        if from_date_created:
            params["created__gte"] = from_date_created.replace("/", "-")
        if until_date_created:
            params["created__lte"] = until_date_created.replace("/", "-")
        if from_date_updated:
            params["updated__gte"] = from_date_updated.replace("/", "-")
        if until_date_updated:
            params["updated__lte"] = until_date_updated.replace("/", "-")
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

    def get_serializer_class(self):
        format_param = self.request.query_params.get("formats")
        if format_param == "articlemeta":
            return ArticleMetaFormatIssueSerializer
        return IssueSerializer