from rest_framework import serializers

from institution.models import Sponsor, Publisher


class SponsorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="institution.institution_identification")

    class Meta:
        model = Publisher
        fields = [
            "name",
        ]

class PublisherSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="institution.institution_identification")

    class Meta:
        model = Publisher
        fields = [
            "name",
        ]