from rest_framework import serializers

from article.api.v1.serializers import ArticleSerializer
from pid_provider.models import PidProviderXML, XMLIssue, XMLJournal


class XMLJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = XMLJournal
        fields = (
            "title",
            "issn_electronic",
            "issn_print",
        )


class XMLIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = XMLIssue
        fields = (
            "volume",
            "number",
            "suppl",
            "pub_year",
        )


class PidProviderXMLSerializer(serializers.ModelSerializer):
    journal = XMLJournalSerializer()
    issue = XMLIssueSerializer()
    article = ArticleSerializer()

    class Meta:
        model = PidProviderXML
        fields = (
            "v2",
            "aop_pid",
            "v3",
            "created",
            "updated",
            "journal",
            "issue",
        )
