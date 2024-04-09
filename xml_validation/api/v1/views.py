from django.db.models import Q
from rest_framework import viewsets


from .serializers import ValidationConfigurationSerializer
from xml_validation.models import ValidationConfiguration


class GenericValidationConfigViewSet(viewsets.ModelViewSet):
    serializer_class = ValidationConfigurationSerializer
    http_method_names = ["get"]
    queryset = ValidationConfiguration.objects.all()