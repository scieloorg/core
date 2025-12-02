from rest_framework import serializers
from organization import models
from wagtail.models.sites import Site
from core.utils.utils import get_url_file_from_image_field


class OrganizationSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        if obj.logo:
            return get_url_file_from_image_field(obj.logo)
        return None

    def get_location(self, obj):
        if obj.location:
            return obj.location.data

    class Meta:
        model = models.Organization
        fields = [
            "name",
            "acronym",
            "url",
            "logo_url",
            "location",
        ]