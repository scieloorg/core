from rest_framework import viewsets

from collection import models
from core.validators import validate_params
from core.utils.utils import params_api
from .serializers import CollectionSerializer


class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    http_method_names = ["get"]
    queryset = models.Collection.objects.all()

    def get_queryset(self):
        acron2 = self.request.query_params.get("acron2")
        acron3 = self.request.query_params.get("acron3")
        main_name = self.request.query_params.get("main_name")
        from_date_created = self.request.query_params.get("from_date_created")
        until_date_created = self.request.query_params.get("until_date_created")
        from_date_updated = self.request.query_params.get("from_date_updated")
        until_date_updated = self.request.query_params.get("until_date_updated")

        validate_params(
            self.request,
            "acron2",
            "acron3",
            "main_name",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",            
            "page",
            "",
        )

        queryset = super().get_queryset()
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
        return queryset.filter(**params)