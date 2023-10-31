from rest_framework import serializers

from reference.models import JournalTitle

class JournalTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalTitle
        fields = [
            "title",
        ]