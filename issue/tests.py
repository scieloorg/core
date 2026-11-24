import json

from django.db import IntegrityError, connection
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from article.models import Article
from collection.models import Collection
from core.models import Gender, Language, License
from core.utils.legacy_record_unique import remove_duplicates
from core.users.models import User
from core.utils.rename_dictionary_keys import rename_issue_dictionary_keys
from editorialboard.models import RoleModel
from issue.articlemeta.correspondencia import correspondencia_issue
from issue.articlemeta.loader import create_issue_from_am_issue, load_am_issue
from issue.articlemeta.issue_utils import extract_data_from_harvested_data
from issue.formats.articlemeta_format import (
    ArticlemetaIssueFormatter,
    get_articlemeta_format_issue,
)
from issue.controller import migrate_issue_legacy_keys
from issue.models import AMIssue, Issue
from journal.models import (
    AMJournal,
    DigitalPreservationAgency,
    IndexedAt,
    Journal,
    SciELOJournal,
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
        issue_data = extract_data_from_harvested_data(
            self.data_issue,
            self.issue_json["issue"]["code"],
        )
        self.issue = Issue.get_or_create(
            user=self.user,
            journal=Journal.objects.first(),
            volume=issue_data.get("volume"),
            number=issue_data.get("number"),
            season=issue_data.get("season"),
            year=issue_data.get("year"),
            month=issue_data.get("month"),
            supplement=issue_data.get("supplement"),
            markup_done=issue_data.get("markup_done"),
            order=issue_data.get("order"),
        )
        self.issue.add_sections(
            self.user,
            issue_data.get("sections_data"),
            self.collection_scl,
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
            pid="0034-8910",
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


class IssueLegacyKeysMixin:
    """
    O issue_pid (AMIssue.pid) é formado por issn_scielo + ano + ordem (4 dígitos)
    e pode divergir entre coleções.
    """

    def setUp(self):
        self.user = User.objects.create(username="teste_legacy", password="teste")
        self.scl = Collection.objects.create(
            creator=self.user, acron3="scl", is_active=True
        )
        self.psi = Collection.objects.create(
            creator=self.user, acron3="psi", is_active=True
        )
        self.journal = Journal.objects.create(creator=self.user, title="Psicologia USP")
        SciELOJournal.objects.create(
            issn_scielo="0103-6564",
            collection=self.scl,
            journal=self.journal,
            journal_acron="pusp",
        )
        SciELOJournal.objects.create(
            issn_scielo="1678-5177",
            collection=self.psi,
            journal=self.journal,
            journal_acron="psicousp",
        )

    def _create_issue(self, number="2", supplement=None, year="2024", migrated=False):
        return Issue.create(
            user=self.user,
            journal=self.journal,
            number=number,
            volume="35",
            season=None,
            year=year,
            month=None,
            supplement=supplement,
            migrated=migrated,
        )

    def _pids(self, issue):
        return {
            item.collection.acron3: item.pid for item in issue.legacy_issue.all()
        }


class TestIssueLegacyKeys(IssueLegacyKeysMixin, TestCase):

    def test_create_issue_creates_am_issue_for_each_collection(self):
        issue = self._create_issue()
        self.assertEqual(
            {"scl": "0103-656420240002", "psi": "1678-517720240002"},
            self._pids(issue),
        )
        self.assertTrue(
            all(item.status == "done" for item in issue.legacy_issue.all())
        )

    def test_save_does_not_duplicate_am_issue(self):
        issue = self._create_issue()
        issue.save()
        issue.save()
        self.assertEqual(2, issue.legacy_issue.count())

    def test_new_issue_has_issue_pid_suffix(self):
        issue = self._create_issue()
        self.assertEqual("0002", issue.issue_pid_suffix)

    def test_generated_pid_uses_next_free_order_in_collection(self):
        # pid 0002 já usado em scl por outro fascículo (ex.: suplemento migrado)
        AMIssue.objects.create(
            pid="0103-656420240002",
            collection=self.scl,
            url="https://articlemeta.scielo.org/api/v1/issue/?code=0103-656420240002",
            creator=self.user,
        )
        issue = self._create_issue()
        # issue_pid_suffix segue a regra (número 2), mesmo que não seja o pid
        self.assertEqual("0002", issue.issue_pid_suffix)
        # em scl, 0002 está em uso: próxima ordem livre
        self.assertEqual(
            {"scl": "0103-656420240003", "psi": "1678-517720240002"},
            self._pids(issue),
        )

    def test_migrated_issue_has_issue_pid_suffix_but_no_generated_pids(self):
        issue = self._create_issue(migrated=True)
        self.assertEqual("0002", issue.issue_pid_suffix)
        self.assertEqual({}, self._pids(issue))

    def test_migrated_issue_gets_pid_by_collection_on_migration(self):
        issue = self._create_issue(migrated=True)
        issue.add_am_issue(
            self.user,
            AMIssue.objects.create(
                pid="1678-517720240005",
                collection=self.psi,
                url="https://articlemeta.scielo.org/api/v1/issue/?code=1678-517720240005",
                creator=self.user,
            ),
        )
        migrate_issue_legacy_keys(self.user, link_am_issues=False)
        # a ordem manual de psi (0005) não é usada em scl
        self.assertEqual(
            {"scl": "0103-656420240002", "psi": "1678-517720240005"},
            self._pids(issue),
        )

    def test_migration_fixes_issue_pid_suffix_of_migrated_issue(self):
        # Issue migrado antes desta mudança: suffix copiado do pid de uma coleção
        issue = self._create_issue(migrated=True)
        Issue.objects.filter(pk=issue.pk).update(issue_pid_suffix="0005")
        issue.add_am_issue(
            self.user,
            AMIssue.objects.create(
                pid="1678-517720240005",
                collection=self.psi,
                url="https://articlemeta.scielo.org/api/v1/issue/?code=1678-517720240005",
                creator=self.user,
            ),
        )
        new_issue = self._create_issue(number="3")

        stats = migrate_issue_legacy_keys(self.user, link_am_issues=False)

        self.assertEqual(1, stats["issue_pid_suffix_fixed"])
        issue.refresh_from_db()
        new_issue.refresh_from_db()
        # recalculado pela regra; o pid estabelecido (0005) continua no AMIssue
        self.assertEqual("0002", issue.issue_pid_suffix)
        self.assertEqual("1678-517720240005", issue.get_issue_pid(self.psi))
        self.assertEqual("0003", new_issue.issue_pid_suffix)
        # pid novo em scl usa issue_pid_suffix, não a ordem manual de psi
        self.assertEqual("0103-656420240002", issue.get_issue_pid(self.scl))

    def test_migrated_am_issue_replaces_generated(self):
        issue = self._create_issue()
        am_issue = AMIssue.objects.create(
            pid="0103-656420240005",
            collection=self.scl,
            url="https://articlemeta.scielo.org/api/v1/issue/?code=0103-656420240005",
            creator=self.user,
        )
        issue.add_am_issue(self.user, am_issue)
        self.assertEqual(
            {"scl": "0103-656420240005", "psi": "1678-517720240002"},
            self._pids(issue),
        )

    def test_migrate_issue_legacy_keys_creates_missing(self):
        issue = self._create_issue()
        # simula Issue criado antes da existência do AMIssue
        issue.legacy_issue.all().delete()
        AMIssue.objects.create(
            pid="1678-517720240007",
            collection=self.psi,
            url="https://articlemeta.scielo.org/api/v1/issue/?code=1678-517720240007",
            new_record=issue,
            creator=self.user,
        )

        stats = migrate_issue_legacy_keys(self.user, link_am_issues=False)

        self.assertEqual(1, stats["issues_processed"])
        self.assertEqual(
            {"scl": "0103-656420240002", "psi": "1678-517720240007"},
            self._pids(issue),
        )
        # execução repetida não processa issues já completos
        stats = migrate_issue_legacy_keys(self.user, link_am_issues=False)
        self.assertEqual(0, stats["issues_processed"])

    def test_get_issue_pid_by_collection(self):
        issue = self._create_issue()
        am_issue = AMIssue.objects.create(
            pid="1678-517720240009",
            collection=self.psi,
            url="https://articlemeta.scielo.org/api/v1/issue/?code=1678-517720240009",
            creator=self.user,
        )
        issue.add_am_issue(self.user, am_issue)
        self.assertEqual("0103-656420240002", issue.get_issue_pid(self.scl))
        self.assertEqual("1678-517720240009", issue.get_issue_pid("psi"))

    def test_articlemeta_format_code_uses_issue_pid_of_collection(self):
        issue = self._create_issue()
        am_issue = AMIssue.objects.create(
            pid="1678-517720240009",
            collection=self.psi,
            url="https://articlemeta.scielo.org/api/v1/issue/?code=1678-517720240009",
            creator=self.user,
        )
        issue.add_am_issue(self.user, am_issue)
        formatter = ArticlemetaIssueFormatter(issue, "psi")
        formatter._format_code("1678-5177")
        self.assertEqual("1678-517720240009", formatter.result["code"])
        formatter = ArticlemetaIssueFormatter(issue, "scl")
        formatter._format_code("0103-6564")
        self.assertEqual("0103-656420240002", formatter.result["code"])


class TestIssueAPIVersions(IssueLegacyKeysMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.issue = self._create_issue()
        am_issue = AMIssue.objects.create(
            pid="1678-517720240009",
            collection=self.psi,
            url="https://articlemeta.scielo.org/api/v1/issue/?code=1678-517720240009",
            creator=self.user,
        )
        self.issue.add_am_issue(self.user, am_issue)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _get(self, url):
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        return response.json()["results"][0]

    def test_v1_issue_pid_suffix_is_the_model_field(self):
        # psi tem pid estabelecido 0009, mas issue_pid_suffix segue a regra
        item = self._get("/api/v1/issue/?collection=psi")
        self.assertEqual("0002", item["issue_pid_suffix"])
        self.assertNotIn("issue_pid", item)

    def test_v2_without_collection_returns_all_legacy_issues(self):
        item = self._get("/api/v2/issue/")
        self.assertIsNone(item["issue_pid"])
        self.assertEqual(
            {"scl": "0103-656420240002", "psi": "1678-517720240009"},
            {key["collection"]: key["pid"] for key in item["legacy_issue"]},
        )

    def test_v2_route_has_no_language_prefix(self):
        self.assertEqual(
            "/api/v2/issue/", reverse("api_v2:Issue-list")
        )

    def test_v2_returns_issue_pid_by_collection(self):
        item = self._get("/api/v2/issue/?collection=psi")
        self.assertEqual("1678-517720240009", item["issue_pid"])
        self.assertEqual("0002", item["issue_pid_suffix"])
        self.assertEqual(
            {"scl": "0103-656420240002", "psi": "1678-517720240009"},
            {key["collection"]: key["pid"] for key in item["legacy_issue"]},
        )
        item = self._get("/api/v2/issue/?collection=scl")
        self.assertEqual("0103-656420240002", item["issue_pid"])
        # legacy_issue não é filtrado pela coleção
        self.assertEqual(2, len(item["legacy_issue"]))


class TestIssueLoadedFromArticleMetaInCollections(IssueLegacyKeysMixin, TestCase):
    """
    O mesmo fascículo coletado do AM em coleções diferentes gera um único
    Issue e um AMIssue por coleção.
    """

    def _load(self, collection, pid, number="2", supplement=None):
        issue = {
            "v31": [{"_": "35"}],
            "v32": [{"_": number}],
            "v65": [{"_": "20240000"}],
        }
        if supplement:
            issue["v131"] = [{"_": supplement}]
        am_issue = load_am_issue(
            self.user,
            collection,
            f"https://articlemeta.scielo.org/api/v1/issue/?code={pid}",
            pid,
            processing_date="2024-01-01",
            harvested_data={"data": {"issue": issue}, "status": "pending"},
            force_update=True,
        )
        return create_issue_from_am_issue(self.user, am_issue)

    def test_one_issue_and_one_am_issue_per_collection(self):
        issue_scl = self._load(self.scl, "0103-656420240005")
        issue_psi = self._load(self.psi, "1678-517720240002")
        # coletas repetidas não duplicam
        self._load(self.scl, "0103-656420240005")
        self._load(self.psi, "1678-517720240002")

        self.assertEqual(issue_scl.pk, issue_psi.pk)
        self.assertEqual(1, Issue.objects.count())
        self.assertEqual(2, AMIssue.objects.count())
        self.assertEqual(
            {"scl": "0103-656420240005", "psi": "1678-517720240002"},
            self._pids(issue_scl),
        )

    def test_absent_identification_is_not_a_wildcard(self):
        issue = self._load(self.scl, "0103-656420240002")
        supplement = self._load(self.scl, "0103-656420241002", supplement="1")
        self.assertNotEqual(issue.pk, supplement.pk)
        self.assertEqual(
            issue,
            Issue.get(self.journal, "2024", volume="35", number="2", supplement=None),
        )
        with self.assertRaises(Issue.DoesNotExist):
            Issue.get(self.journal, "2024", volume="35", number=None)

    def test_legacy_pid_used_by_generated_pid_of_other_issue(self):
        # Issue novo: pid gerado em scl 0103-656420240002
        new_issue = self._create_issue(number="2")
        # no legado, 0103-656420240002 é o pid manual do número 3 em scl
        legacy_issue = self._load(self.scl, "0103-656420240002", number="3")

        self.assertNotEqual(new_issue.pk, legacy_issue.pk)
        self.assertEqual({"scl": "0103-656420240002"}, self._pids(legacy_issue))
        # o Issue novo recebe outro pid em scl
        self.assertEqual(
            {"scl": "0103-656420240003", "psi": "1678-517720240002"},
            self._pids(new_issue),
        )
        self.assertEqual(
            1,
            AMIssue.objects.filter(collection=self.scl, pid="0103-656420240002").count(),
        )

    def test_am_issue_is_unique_by_collection_and_pid(self):
        AMIssue.create_or_update("0103-656420240005", self.scl, user=self.user)
        AMIssue.create_or_update("0103-656420240005", self.scl, user=self.user)
        AMIssue.create_or_update("0103-656420240005", self.psi, user=self.user)
        self.assertEqual(2, AMIssue.objects.count())
        with self.assertRaises(IntegrityError):
            AMIssue.objects.create(
                pid="0103-656420240005", collection=self.scl, creator=self.user
            )


class TestRemoveDuplicatedAMIssues(IssueLegacyKeysMixin, TestCase):
    """
    Remoção de duplicados feita pela migração issue.0022 antes de criar
    unique (collection, pid).
    """

    def setUp(self):
        super().setUp()
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE issue_amissue DROP CONSTRAINT unique_amissue_collection_pid"
            )

    def _am_issue(self, collection, **kwargs):
        return AMIssue.objects.create(
            pid="0103-656420240005", collection=collection, creator=self.user, **kwargs
        )

    def test_keeps_migrated_and_inherits_new_record(self):
        issue = self._create_issue(migrated=True)
        generated = self._am_issue(self.scl, new_record=issue)
        migrated = self._am_issue(
            self.scl, url="https://articlemeta.scielo.org/api/v1/issue/?code=x"
        )
        linked = self._am_issue(self.scl, data={"issue": {}}, new_record=issue)
        other_collection = self._am_issue(self.psi)

        removed = remove_duplicates(AMIssue)

        self.assertEqual(2, removed)
        self.assertEqual(
            {linked.pk, other_collection.pk},
            set(AMIssue.objects.values_list("pk", flat=True)),
        )
        self.assertFalse(AMIssue.objects.filter(pk__in=[generated.pk, migrated.pk]).exists())

    def test_migrated_without_new_record_inherits_it(self):
        issue = self._create_issue(migrated=True)
        kept = self._am_issue(self.scl, data={"issue": {}})
        self._am_issue(
            self.scl,
            url="https://articlemeta.scielo.org/api/v1/issue/?code=x",
            new_record=issue,
        )

        remove_duplicates(AMIssue)

        self.assertEqual([kept.pk], list(AMIssue.objects.values_list("pk", flat=True)))
        kept.refresh_from_db()
        self.assertEqual(issue, kept.new_record)
