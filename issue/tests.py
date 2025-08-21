import json

from django.test import TestCase

from article.models import Article
from collection.models import Collection
from core.models import Gender, Language, License
from core.users.models import User
from core.utils.rename_dictionary_keys import rename_issue_dictionary_keys
from editorialboard.models import RoleModel
from issue.formats.articlemeta_format import get_articlemeta_format_issue
from issue.models import Issue
from issue.utils.correspondencia import correspondencia_issue
from issue.utils.issue_utils import get_or_create_issue
from journal.models import (
    AMJournal,
    DigitalPreservationAgency,
    IndexedAt,
    Journal,
    Standard,
    Subject,
    WebOfKnowledge,
    WebOfKnowledgeSubjectCategory,
)
from journal.tasks import _register_journal_data
from thematic_areas.models import ThematicArea
from vocabulary.models import Vocabulary


def sort_any(obj):
    if isinstance(obj, dict):
        return {k: sort_any(v).lower() for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        if all(isinstance(i, dict) for i in obj):
            return sorted((sort_any(i) for i in obj), key=lambda x: json.dumps(x, sort_keys=True))
        elif all(not isinstance(i, dict) for i in obj):
            return sorted(obj)
        else:
            return [sort_any(i) for i in obj]
    else:
        return obj

class TestAPIIssueArticleMeta(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.issue_json = json.loads(open("./issue/fixture/tests/api_articlemeta_issue.json").read())
        self.data_issue = rename_issue_dictionary_keys(
            [self.issue_json["issue"]], correspondencia_issue
        )
        self.setUp_journal()
        self.issue = get_or_create_issue(
            issn_scielo=self.data_issue.get("scielo_issn"),
            volume=self.data_issue.get("volume"),
            number=self.data_issue.get("number"),
            supplement_volume=self.data_issue.get("supplement_volume"),
            supplement_number=self.data_issue.get("supplement_number"),
            data_iso=self.data_issue.get("date_iso"),
            sections_data=self.data_issue.get("sections_data"),
            markup_done=self.data_issue.get("markup_done"),
            order="1001",
            user=self.user,
        )
        self.include_articlemeta_metadata(data_json=self.issue_json, issue=self.issue)
        self.article = Article.objects.create(
            pid_v2="S0034-891020180002",
            issue=Issue.objects.first(),
            creator=self.user,
            journal=Journal.objects.first(),
        )

    def setUp_journal(self):
        self.collection_spa = Collection.objects.create(
            acron3="spa",
            code="spa",
            is_active=True,
            domain="www.scielosp.org",
        )
        self.collection_scl = Collection.objects.create(
            acron3="scl",
            code="scl",
            is_active=True,
            domain="www.scielo.br",
        )
        self.journal_scl = AMJournal.objects.create(
            collection=Collection.objects.get(acron3="scl"),
            scielo_issn="0034-8910",
            data=json.loads(open("./journal/fixture/tests/data_journal_scl_0034-8910.json").read()),
            creator=self.user,
        )
        self.load_standards()
    
    def load_standards(self):
        self.load_modules()
        _register_journal_data(self.user, self.collection_scl.acron3)

    def load_modules(self):
        Language.load(self.user)
        Vocabulary.load(self.user)
        Standard.load(self.user)
        Subject.load(self.user)
        WebOfKnowledge.load(self.user)
        ThematicArea.load(self.user)
        WebOfKnowledgeSubjectCategory.load(self.user)
        IndexedAt.load(self.user)
        RoleModel.load(self.user)
        License.load(self.user)
        DigitalPreservationAgency.load(self.user)
        Gender.load(self.user)

    def include_articlemeta_metadata(self, data_json, issue):
        data_json["created_at"] = issue.created.strftime('%Y-%m-%d')
        data_json["processing_date"] = issue.created.strftime('%Y-%m-%d')
        data_json['issue']["v91"] = [{"_": issue.created.strftime('%Y%m%d')}]
        data_json['issue']["processing_date"] = issue.created.strftime('%Y-%m-%d')
        data_json['title']["created_at"] = issue.created.strftime('%Y-%m-%d')
        data_json['title']["processing_date"] = issue.created.strftime('%Y-%m-%d')
        data_json['title']["v940"] = [{"_": issue.created.strftime('%Y%m%d')}]
        data_json['title']["v941"] = [{"_": issue.updated.strftime('%Y%m%d')}]
        data_json['title']["v942"] = [{"_": issue.created.strftime('%Y%m%d')}]
        data_json['title']["v943"] = [{"_": issue.updated.strftime('%Y%m%d')}]
        if "v691" in data_json['title']:
            del data_json["title"]["v691"]

    def get_articlemeta_format_issue(self, key, expected_sorted, result_sorted):
        expected_sorted = sort_any(expected_sorted)
        result_sorted = sort_any(result_sorted)
        self.assertEqual(
            result_sorted, expected_sorted,
            f"Key {key} not equal. Expected: {expected_sorted}, Result: {result_sorted}"
        )

    def test_articlemeta_format(self):
        formatter = get_articlemeta_format_issue(Issue.objects.first(), collection="scl")
        for key in self.issue_json.keys():
            if key == "issue" or key == "title":
                continue
            with self.subTest(key=key):
                expected = self.issue_json.get(key)
                result = formatter.get(key)
                self.get_articlemeta_format_issue(key, expected, result)

    def test_articlemeta_format_key_issue(self):
        formatter = get_articlemeta_format_issue(Issue.objects.first(), collection="scl")
        for key in self.issue_json['issue'].keys():
            with self.subTest(key=key):
                expected = self.issue_json['issue'].get(key)
                result = formatter['issue'].get(key)
                self.get_articlemeta_format_issue(key, expected, result)

    def test_articlemeta_format_key_title(self):
        formatter = get_articlemeta_format_issue(Issue.objects.first(), collection="scl")
        for key in self.issue_json['title'].keys():
            with self.subTest(key=key):
                expected = self.issue_json['title'].get(key)
                result = formatter['title'].get(key)
                self.get_articlemeta_format_issue(key, expected, result)