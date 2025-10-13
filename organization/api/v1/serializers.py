from rest_framework import serializers
from organization import models
from wagtail.models.sites import Site

class OrganizationSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        if obj.logo:
            domain = Site.objects.get(is_default_site=True).hostname
            domain = f"http://{domain}"
            return f"{domain}{obj.logo.url}"
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