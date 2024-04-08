from rest_framework import serializers

from xml_validation.models import ValidationConfiguration


class ValidationConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationConfiguration
        fields = [
            "key",
            "value",
        ]