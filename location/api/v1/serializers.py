from rest_framework import serializers

from location import models


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.City
        fields = [
            "name",
        ]