import json
from unittest.mock import patch

from django.test import TestCase
from django_test_migrations.migrator import Migrator

from collection.models import Collection
from core.models import Gender, Language, License
from core.users.models import User
from editorialboard.models import RoleModel
from journal.formats.articlemeta_format import get_articlemeta_format_title
from journal.models import (
    AMJournal,
    DigitalPreservationAgency,
    IndexedAt,
    Journal,
    JournalLicense,
    SciELOJournal,
    Standard,
    Subject,
    WebOfKnowledge,
    WebOfKnowledgeSubjectCategory,
)
from journal.tasks import (
    _register_journal_data,
    child_load_license_of_use_in_journal,
    load_license_of_use_in_journal,
)
from thematic_areas.models import ThematicArea
from vocabulary.models import Vocabulary


class MigrationTestCase(TestCase):
    def test_migration_adding_journal_urls(self):
        migrator = Migrator(database="default")
        old_state = migrator.apply_initial_migration(
            ("journal", "0024_alter_officialjournal_issn_electronic_and_more")
        )
        Journal = old_state.apps.get_model("journal", "Journal")
        JournalURL = old_state.apps.get_model("journal", "JournalURL")

        journal = Journal.objects.create(journal_url="https://www.teste.com.br")

        new_state = migrator.apply_tested_migration(("journal", "0025_journalurl"))
        JournalURL = new_state.apps.get_model("journal", "JournalURL")

        journal_url = JournalURL.objects.filter(journal=journal).first()
        self.assertIsNotNone(journal_url)
        self.assertEqual(journal_url.url, "https://www.teste.com.br")

    def test_reverse_migration_deleting_journal_urls(self):
        migrator = Migrator(database="default")
        new_state = migrator.apply_initial_migration(("journal", "0025_journalurl"))
        JournalURL = new_state.apps.get_model("journal", "JournalURL")
        Journal = new_state.apps.get_model("journal", "Journal")

        journal = Journal.objects.create(name="Test Journal")
        JournalURL.objects.create(journal=journal, url="http://example.com")

        journal_url = JournalURL.objects.filter(journal=journal).first()
        self.assertIsNotNone(journal_url)

        old_state = migrator.apply_tested_migration(
            ("journal", "0024_alter_officialjournal_issn_electronic_and_more")
        )
        JournalURL = old_state.apps.get_model("journal", "JournalURL")

        journal_url = JournalURL.objects.filter(journal=journal).first()
        self.assertIsNone(journal_url)

        migrator.reset()


class TestLoadLicenseOfUseInJournal(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.collection = Collection.objects.create(
            creator=self.user, acron3="scl", is_active=True
        )
        self.journal = Journal.objects.create(creator=self.user, title="Test Journal")
        self.am_journal = AMJournal.objects.create(
            collection=self.collection,
            scielo_issn="1516-635X",
            data=[
                {
                    "v541": [{"_": "BY"}],
                }
            ],
        )
        self.scielo_journal = SciELOJournal.objects.create(
            issn_scielo="1516-635X",
            collection=self.collection,
            journal=self.journal,
            journal_acron="abdc",
        )

    @patch("journal.tasks.child_load_license_of_use_in_journal.apply_async")
    def test_load_license_of_use_in_journal(self, mock_apply_async):
        load_license_of_use_in_journal(
            collection_acron3=self.collection.acron3,
            username=self.user.username,
        )

        mock_apply_async.assert_called_once_with(
            kwargs={
                "user_id": None,
                "username": self.user.username,
                "journal_issn": "1516-635X",
                "license_data": "BY",
            }
        )

    @patch("journal.tasks.child_load_license_of_use_in_journal.apply_async")
    def test_load_license_of_use_in_journal_with_none_scielo_issn(
        self, mock_apply_async
    ):
        self.am_journal_2 = AMJournal.objects.create(
            collection=self.collection,
            scielo_issn=None,
            data=[
                {
                    "v541": [{"_": "BY"}],
                }
            ],
        )
        load_license_of_use_in_journal(
            username=self.user.username,
        )
        mock_apply_async.assert_called_once_with(
            kwargs={
                "user_id": None,
                "username": self.user.username,
                "journal_issn": "1516-635X",
                "license_data": "BY",
            }
        )

    def test_child_load_license_of_use_in_journal(self):
        child_load_license_of_use_in_journal(
            license_data="BY",
            username=self.user.username,
            journal_issn=self.scielo_journal.issn_scielo,
            user_id=None,
        )
        self.journal.refresh_from_db()
        journal_license = JournalLicense.objects.all()
        self.assertEqual(journal_license.count(), 1)
        self.assertEqual(self.journal.journal_use_license, journal_license.first())
        self.assertEqual(self.journal.journal_use_license.license_type, "BY")

    def test_child_load_license_of_use_in_journal_with_none_license(self):
        child_load_license_of_use_in_journal(
            license_data=None,
            username=self.user.username,
            journal_issn=self.scielo_journal.issn_scielo,
            user_id=None,
        )
        self.journal.refresh_from_db()
        journal_license = JournalLicense.objects.all()
        self.assertEqual(journal_license.count(), 0)
        self.assertEqual(self.journal.journal_use_license, None)

import json

def sort_any(obj):
    if isinstance(obj, dict):
        return {k: sort_any(v.lower()) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        if all(isinstance(i, dict) for i in obj):
            return sorted((sort_any(i) for i in obj), key=lambda x: json.dumps(x, sort_keys=True))
        elif all(not isinstance(i, dict) for i in obj):
            return sorted(obj)
        else:
            return [sort_any(i) for i in obj]
    else:
        return obj

class TestAPIJournalArticleMeta(TestCase):
    def setUp(self):
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
        self.data_json_journal_scl = json.loads(open("./journal/fixture/tests/data_journal_scl_0034-8910.json").read())
        self.user = User.objects.create(username="teste", password="teste")
        self.am_journal_scl = AMJournal.objects.create(
            collection=Collection.objects.get(acron3="scl"),
            scielo_issn="0034-8910",
            data=self.data_json_journal_scl,
            creator=self.user,
        )
        self.load_standards()

    def set_journals(self):
        self.journal_scl = SciELOJournal.objects.get(collection__acron3="scl").journal

    def load_standards(self):
        self.load_modules()
        _register_journal_data(self.user, self.collection_scl.acron3)
        _register_journal_data(self.user, self.collection_spa.acron3)
        self.set_journals()
        self.include_articlemeta_metadata(data_json=self.data_json_journal_scl[0], journal=self.journal_scl)

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
    
    def include_articlemeta_metadata(self, data_json, journal):
        data_json["created_at"] = journal.created.strftime('%Y-%m-%d')
        data_json["processing_date"] = journal.created.strftime('%Y-%m-%d')
        data_json["v940"] = [{"_": journal.created.strftime('%Y%m%d')}]
        data_json["v941"] = [{"_": journal.updated.strftime('%Y%m%d')}]
        data_json["v942"] = [{"_": journal.created.strftime('%Y%m%d')}]
        data_json["v943"] = [{"_": journal.updated.strftime('%Y%m%d')}]
        if "v691" in data_json:
            del data_json["v691"]

    def test_load_journal_scl_from_article_meta(self):
        formatter = get_articlemeta_format_title(self.journal_scl, collection="scl")
        for key in self.data_json_journal_scl[0].keys():
            with self.subTest(key=key):
                expected = self.data_json_journal_scl[0].get(key)
                result = formatter.get(key)
                expected_sorted = sort_any(expected)
                result_sorted = sort_any(result)
                self.assertEqual(
                    result_sorted, expected_sorted,
                    f"Key {key} not equal. Expected: {expected_sorted}, Result: {result_sorted}"
        )
