import json
from unittest.mock import patch

from django.test import TestCase
from django_test_migrations.migrator import Migrator

from collection.models import Collection
from core.users.models import User
from journal.models import AMJournal, Journal, JournalLicense, SciELOJournal
from journal.tasks import (
    child_load_license_of_use_in_journal,
    load_license_of_use_in_journal,
)


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
