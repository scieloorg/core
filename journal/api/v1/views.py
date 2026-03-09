from rest_framework import serializers, viewsets
from django.db.models import F, Prefetch, Q

from core.utils.utils import formated_date_api_params
from core.validators import validate_params
from journal import models

from .serializers import CrossmarkPolicySerializer, JournalSerializer


class ArticleMetaFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Journal

    def to_representation(self, instance):
        collection = getattr(instance, 'collection_acron', None)
        return instance.articlemeta_format(collection)

    
class GenericJournalViewSet(viewsets.ModelViewSet):
    serializer_class = JournalSerializer
    http_method_names = ["get"]
    queryset = models.Journal.objects.prefetch_related(
        Prefetch(
            "crossmark_policy",
            queryset=models.CrossmarkPolicy.objects
            .select_related("language", "journal__official")
            .prefetch_related(
                Prefetch(
                    "journal__scielojournal_set",
                    queryset=models.SciELOJournal.objects.select_related("collection"),
                )
            ),
        )
    )


class JournalViewSet(GenericJournalViewSet):
    def get_queryset(self):
        query_params = self.request.query_params
        
        validate_params(
            self.request,
            "issn_print",
            "issn_electronic",
            "issn",
            "title",
            "thematic_areas",
            "toc_item",
            "page",
            "collection",
            "from_date_created",
            "until_date_created",
            "from_date_updated",
            "until_date_updated",
            "formats",
            "issnl",
            "",
        )

        params = {}
        if issn := query_params.get("issn"):
           params["scielojournal__issn_scielo"] = issn
        if issn_electronic := query_params.get("issn_electronic"):
           params["official__issn_electronic"] = issn_electronic
        if issn_print := query_params.get("issn_print"):
           params["official__issn_print"] = issn_print
        if issnl := query_params.get("issnl"):
           params["official__issnl"] = issnl
        if title := query_params.get("title"):
           params["title"] = title
        if toc_item := query_params.get("toc_item"):
           params["journaltocsection__toc_items__text"] = toc_item
        if thematic_areas := query_params.get("thematic_areas"):
           params["subject__value__in"] = thematic_areas.split(",")
        if collection_acron := query_params.get("collection"):
           params["scielojournal__collection__acron3"] = collection_acron
        
        formated_date = formated_date_api_params(query_params)
        if formated_date:
            params.update(formated_date)

        query = super().get_queryset()
        if query_params.get("formats") == "articlemeta":
            return query.filter(
                scielojournal__journal__isnull=False
            ).filter(**params).annotate(
                collection_acron=F('scielojournal__collection__acron3')
            ).order_by('created').distinct()
        
        return query.filter(**params).order_by('created').distinct()

    def get_serializer_class(self):
        format_param = self.request.query_params.get("formats")
        if format_param == "articlemeta":
            return ArticleMetaFormatSerializer
        return JournalSerializer

class CrossmarkPolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that exposes CrossmarkPolicy data for journals.

    Supports the following query parameters:
      - issn: filter by any ISSN (eissn or pissn)
      - collection: filter by collection acronym (acron3)
      - journal_acronym: filter by SciELO journal acronym

    **GET /api/v1/crossmarkpolicy/** — list all crossmark policies

    Example response:
    ```json
    {
        "count": 2,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 1,
                "doi": "10.1234/crossmark-policy",
                "is_active": true,
                "language": "pt",
                "rich_text": "<p>Política de atualização do periódico.</p>",
                "url": "https://www.scielo.br/about/policies",
                "journal": 42,
                "journal_issn_print": "1234-5678",
                "journal_issn_electronic": "9876-5432",
                "journal_acronym": "bjmbr"
            },
            {
                "id": 2,
                "doi": null,
                "is_active": false,
                "language": "en",
                "rich_text": "<p>Journal update policy.</p>",
                "url": "https://www.scielo.br/about/policies-en",
                "journal": 42,
                "journal_issn_print": "1234-5678",
                "journal_issn_electronic": "9876-5432",
                "journal_acronym": "bjmbr"
            }
        ]
    }
    ```

    **GET /api/v1/crossmarkpolicy/{id}/** — retrieve a specific crossmark policy

    Example response:
    ```json
    {
        "id": 1,
        "doi": "10.1234/crossmark-policy",
        "is_active": true,
        "language": "pt",
        "rich_text": "<p>Política de atualização do periódico.</p>",
        "url": "https://www.scielo.br/about/policies",
        "journal": 42,
        "journal_issn_print": "1234-5678",
        "journal_issn_electronic": "9876-5432",
        "journal_acronym": "bjmbr"
    }
    ```
    """

    serializer_class = CrossmarkPolicySerializer
    http_method_names = ["get"]
    queryset = (
        models.CrossmarkPolicy.objects
        .select_related("language", "journal", "journal__official")
        .prefetch_related(
            Prefetch(
                "journal__scielojournal_set",
                queryset=models.SciELOJournal.objects.select_related("collection"),
            )
        )
    )

    def get_queryset(self):
        query_params = self.request.query_params

        validate_params(
            self.request,
            "issn",
            "collection",
            "journal_acronym",
            "page",
        )

        params = {}
        issn_filter = None
        if issn := query_params.get("issn"):
            issn_filter = (
                Q(journal__official__issn_electronic=issn)
                | Q(journal__official__issn_print=issn)
            )
        if collection := query_params.get("collection"):
            params["journal__scielojournal__collection__acron3"] = collection
        if journal_acronym := query_params.get("journal_acronym"):
            params["journal__scielojournal__journal_acron"] = journal_acronym

        qs = super().get_queryset().filter(**params)
        if issn_filter is not None:
            qs = qs.filter(issn_filter)
        return qs.distinct()
