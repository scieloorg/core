from rest_framework import serializers

from institution.models import Sponsor


class SponsorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        fields = [
            "name",
            "institution_type",
        ]