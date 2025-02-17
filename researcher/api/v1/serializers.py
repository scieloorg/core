from rest_framework import serializers

from researcher.models import Researcher


class ResearcherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Researcher
        fields = [
            "person_name",
            "affiliation",
            # "gender",
            # "gender_identification_status",
        ]
