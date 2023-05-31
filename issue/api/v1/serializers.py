from rest_framework import serializers
from issue import models


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Issue
        fields = [
            "number",
            "volume",
            "season",
            "year",
            "month",
            "supplement",
        ]