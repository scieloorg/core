from django.test import TestCase

from article.models import AMArticle, Article
from collection.models import Collection
from core.users.models import User
from issue.models import AMIssue, Issue
from journal.models import Journal, SciELOJournal
from pid_provider.models import CollectionPidV2, PidProviderXML


class ArticleLegacyKeysTest(TestCase):
    """
    O pid v2 pode divergir entre coleções; no core é usado o pid v2 enviado
    no XML de cada coleção (CollectionPidV2), sem gerar nem derivar valores.
    Ex.: Psicologia USP
    - scl: S0103-65642024000200003
    - psi: S1678-51772024000500007
    """

    def setUp(self):
        self.user = User.objects.create(username="article_legacy", password="x")
        self.scl = Collection.objects.create(
            creator=self.user, acron3="scl", is_active=True
        )
        self.psi = Collection.objects.create(
            creator=self.user, acron3="psi", is_active=True
        )
        self.journal = Journal.objects.create(creator=self.user, title="Psicologia USP")
        SciELOJournal.objects.create(
            issn_scielo="0103-6564", collection=self.scl, journal=self.journal
        )
        SciELOJournal.objects.create(
            issn_scielo="1678-5177", collection=self.psi, journal=self.journal
        )
        self.issue = Issue.create(
            user=self.user,
            journal=self.journal,
            number="2",
            volume="35",
            season=None,
            year="2024",
            month=None,
            supplement=None,
        )
        # issue_pid de psi diverge do gerado (ordem 0005 em vez de 0002)
        self.issue.add_am_issue(
            self.user,
            AMIssue.objects.create(
                pid="1678-517720240005",
                collection=self.psi,
                url="https://articlemeta.scielo.org/api/v1/issue/?code=1678-517720240005",
                creator=self.user,
            ),
        )
        self.pp_xml = PidProviderXML.objects.create(
            creator=self.user, v3="ARTICLELEGACYKEYSV3XXXX", v2="S0103-65642024000200003"
        )
        self.article = Article.objects.create(
            creator=self.user,
            journal=self.journal,
            issue=self.issue,
            pid_v3=self.pp_xml.v3,
            pid_v2=self.pp_xml.v2,
            pp_xml=self.pp_xml,
        )

    def _pids(self):
        return {
            item.collection.acron3: item.pid
            for item in self.article.legacy_article.all()
        }

    def _add_collection_pid_v2(self, collection, pid_v2):
        CollectionPidV2.objects.create(
            creator=self.user,
            pid_provider_xml=self.pp_xml,
            collection=collection,
            pid_v2=pid_v2,
        )

    def test_uses_pid_v2_from_xml_of_each_collection(self):
        self._add_collection_pid_v2(self.scl, "S0103-65642024000200003")
        self._add_collection_pid_v2(self.psi, "S1678-51772024000500007")

        self.article.create_legacy_keys(self.user)

        self.assertEqual(
            {"scl": "S0103-65642024000200003", "psi": "S1678-51772024000500007"},
            self._pids(),
        )

    def test_collection_without_xml_has_no_pid_v2(self):
        # só o XML de scl foi registrado; psi aguarda o XML da coleção
        self._add_collection_pid_v2(self.scl, "S0103-65642024000200003")

        self.article.create_legacy_keys(self.user)

        self.assertEqual({"scl": "S0103-65642024000200003"}, self._pids())

    def test_without_pp_xml_creates_no_pid_v2(self):
        self.article.pp_xml = None
        self.article.create_legacy_keys(self.user)

        self.assertEqual({}, self._pids())

    def test_replaces_not_migrated_pid_v2_when_xml_changes(self):
        AMArticle.objects.create(
            pid="S1678-51772024000500001",
            collection=self.psi,
            new_record=self.article,
            creator=self.user,
        )
        self._add_collection_pid_v2(self.psi, "S1678-51772024000500007")

        self.article.create_legacy_keys(self.user, force_update=True)

        self.assertEqual(
            ["S1678-51772024000500007"],
            list(
                self.article.legacy_article.filter(collection=self.psi).values_list(
                    "pid", flat=True
                )
            ),
        )

    def test_does_not_duplicate_existing_pid_v2(self):
        self._add_collection_pid_v2(self.scl, "S0103-65642024000200003")

        self.article.create_legacy_keys(self.user)
        self.article.create_legacy_keys(self.user)

        self.assertEqual(
            1,
            AMArticle.objects.filter(
                pid="S0103-65642024000200003", collection=self.scl
            ).count(),
        )

    def test_links_existing_migrated_pid_v2_without_changing_it(self):
        migrated = AMArticle.objects.create(
            pid="S0103-65642024000200003",
            collection=self.scl,
            url="https://articlemeta.scielo.org/api/v1/article/?code=S0103-65642024000200003",
            status="todo",
            creator=self.user,
        )
        self._add_collection_pid_v2(self.scl, "S0103-65642024000200003")

        self.article.create_legacy_keys(self.user)

        migrated.refresh_from_db()
        self.assertEqual(self.article.pk, migrated.new_record_id)
        self.assertEqual("todo", migrated.status)
        self.assertEqual(
            1, AMArticle.objects.filter(pid=migrated.pid, collection=self.scl).count()
        )

    def test_does_not_take_pid_v2_of_another_article(self):
        other = Article.objects.create(creator=self.user, journal=self.journal)
        AMArticle.objects.create(
            pid="S0103-65642024000200003",
            collection=self.scl,
            new_record=other,
            creator=self.user,
        )
        self._add_collection_pid_v2(self.scl, "S0103-65642024000200003")

        self.article.create_legacy_keys(self.user)

        self.assertEqual({}, self._pids())
        self.assertEqual(
            1,
            AMArticle.objects.filter(
                pid="S0103-65642024000200003", collection=self.scl
            ).count(),
        )
