from rest_framework import serializers

from journal import models
from reference.api.v1.serializers import JournalTitleSerializer
from core.api.v1.serializers import LanguageSerializer, LicenseSerializer
from vocabulary.api.v1.serializers import VocabularySerializer


class OfficialJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OfficialJournal
        fields = [
            "title",
            "issn_print",
            "issn_electronic",
            "issnl",
        ]
        datatables_always_serialize = ("id",)


class SubjectDescriptorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubjectDescriptor
        fields = [
            "value",
        ]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Subject
        fields = [
            "code",
            "value",
        ]


class WebOfKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WebOfKnowledge
        fields = [
            "code",
            "value",
        ]


class WebOfKnowledgeSubjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WebOfKnowledgeSubjectCategory
        fields = ["value"]


class StandardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Standard
        fields = [
            "code",
            "value",
        ]


class IndexedAtSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.IndexedAt
        fields = [
            "name",
            "acronym",
            "url",
            "description",
            "type",
        ]


class JournalSerializer(serializers.ModelSerializer):
    # Serializadores para campos de relacionamento, como 'official', devem corresponder aos campos do modelo.
    official = OfficialJournalSerializer(many=False, read_only=True)
    other_titles = JournalTitleSerializer(many=True, read_only=True)
    subject_descriptor = SubjectDescriptorSerializer(many=True, read_only=True)
    subject = SubjectSerializer(many=True, read_only=True)
    wos_db = WebOfKnowledgeSerializer(many=True, read_only=True)
    wos_area = WebOfKnowledgeSubjectCategorySerializer(many=True, read_only=True)
    text_language = LanguageSerializer(many=True, read_only=True)
    abstract_language = LanguageSerializer(many=True, read_only=True)
    standard = StandardSerializer(many=False, read_only=True)
    vocabulary = VocabularySerializer(many=False, read_only=True)
    indexed_at = IndexedAtSerializer(many=True, read_only=True)
    use_license = LicenseSerializer(many=False, read_only=True)

    class Meta:
        model = models.Journal
        fields = [
            "official",
            "title",
            "short_title",
            "other_titles",
            "submission_online_url",
            "open_access",
            "url_oa",
            "collection_main_url",
            "frequency",
            "publishing_model",
            "subject_descriptor",
            "subject",
            "wos_db",
            "wos_area",
            "text_language",
            "abstract_language",
            "standard",
            "alphabet",
            "type_of_literature",
            "treatment_level",
            "level_of_publication",
            "national_code",
            "classification",
            "vocabulary",
            "indexed_at",
            "secs_code",
            "medline_code",
            "medline_short_title",
            "journal_url",
            "use_license",
            "center_code",
            "identification_number",
            "ftp",
            "user_subscription",
            "subtitle",
            "section",
            "has_supplement",
            "is_supplement",
            "acronym_letters",
        ]
        datatables_always_serialize = ("id",)
