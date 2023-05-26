from rest_framework import serializers

from journal.models import ScieloJournal


class JournalSerialiazer(serializers.ModelSerializer):
    class Meta:
        model = ScieloJournal
        fields = [
            "title",
        ]