from rest_framework import serializers

from journal.models import Journal


class JournalSerialiazer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = [
            "title",
        ]
