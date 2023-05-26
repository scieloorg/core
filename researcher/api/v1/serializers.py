from rest_framework import serializers

from researcher.models import Researcher


class ResearcherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Researcher
        fields = [
            "given_names",
            "last_name",
            "suffix",
            "orcid",
            "lattes",
            # "gender",
            # "gender_identification_status",
        ]