from rest_framework import viewsets

from collection import models
from core.validators import validate_params

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
        params = {}
        
        if acron2:
            params["acron2"] = acron2
        if acron3:
            params["acron3"] = acron3
        if main_name:
            params["main_name"] = main_name
        if from_date_created:
            params["created__gte"] = from_date_created.replace("/", "-")
        if until_date_created:
            params["created__lte"] = until_date_created.replace("/", "-")
        if from_date_updated:
            params["updated__gte"] = from_date_updated.replace("/", "-")
        if until_date_updated:
            params["updated__lte"] = until_date_updated.replace("/", "-")            
        return queryset.filter(**params)