from django.db.models import Q
from rest_framework import viewsets

from core.validators import validate_params
from .serializers import ValidationConfigurationSerializer
from xml_validation.models import ValidationConfiguration


class GenericValidationConfigViewSet(viewsets.ModelViewSet):
    serializer_class = ValidationConfigurationSerializer
    http_method_names = ["get"]
    queryset = ValidationConfiguration.objects.all()


class ValidationConfigSerializerView(GenericValidationConfigViewSet):
    def get_queryset(self):
        qs = super().get_queryset()
        version = self.request.query_params.get("version")
        validate_params(self.request, "version")
        try:
            queryset = qs.filter(version__version=version)
        except ValidationConfiguration.DoesNotExist:
            queryset = qs.none()
        return queryset

