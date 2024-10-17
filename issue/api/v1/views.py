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
            "",
        )

        params = params_api(
            scielojournal__issn_scielo=issn,
            official__issn_electronic=issn_electronic,
            official__issn_print=issn_print,
            official__issnl=issnl,
            title=title,
            journaltocsection__toc_items__text=toc_item,
            subject__value__in=thematic_areas.split(",") if thematic_areas else None,
            acron2=acron2,
            acron3=acron3,
            main_name=main_name,
            created__gte=from_date_created.replace("/", "-") if from_date_created else None,
            created__lte=until_date_created.replace("/", "-") if until_date_created else None,
            updated__gte=from_date_updated.replace("/", "-") if from_date_updated else None,
            updated__lte=until_date_updated.replace("/", "-") if until_date_updated else None
        )

        return queryset 

    