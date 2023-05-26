from rest_framework import serializers


from journal.api.v1.serializers import JournalSerialiazer
from issue.models import Issue


class IssueSerializer(serializers.ModelSerializer):
    journal = JournalSerialiazer(many=False, read_only=False)

    class Meta:
        model = Issue
        fields = [
            "journal",
            "number",
            "volume",
            "season",
            "year",
            "month",
            "supplement",
        ]