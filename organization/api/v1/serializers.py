from rest_framework import serializers
from organization import models


class OrganizationSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()

    def get_location(self, obj):
        if obj.location:
            return obj.location.data

    class Meta:
        model = models.Organization
        fields = [
            "name",
            "acronym",
            "location",
        ]