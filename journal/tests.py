from django.test import TestCase
from django_test_migrations.migrator import Migrator

class MigrationTestCase(TestCase):
    def test_migration_adding_journal_urls(self):
        migrator = Migrator(database='default')
        old_state = migrator.apply_initial_migration(('journal', '0024_alter_officialjournal_issn_electronic_and_more'))
        Journal = old_state.apps.get_model('journal', 'Journal')
        JournalURL = old_state.apps.get_model('journal', 'JournalURL')

        journal = Journal.objects.create(journal_url="https://www.teste.com.br")

        new_state = migrator.apply_tested_migration(('journal', '0025_journalurl'))
        JournalURL = new_state.apps.get_model('journal', 'JournalURL')

        journal_url = JournalURL.objects.filter(journal=journal).first()
        self.assertIsNotNone(journal_url)
        self.assertEqual(journal_url.url, "https://www.teste.com.br")

    def test_reverse_migration_deleting_journal_urls(self):
        migrator = Migrator(database='default')
        new_state = migrator.apply_initial_migration(('journal', '0025_journalurl'))
        JournalURL = new_state.apps.get_model('journal', 'JournalURL')
        Journal = new_state.apps.get_model('journal', 'Journal')

        journal = Journal.objects.create(name="Test Journal")
        JournalURL.objects.create(journal=journal, url="http://example.com")

        journal_url = JournalURL.objects.filter(journal=journal).first()
        self.assertIsNotNone(journal_url)

        old_state = migrator.apply_tested_migration(('journal', '0024_alter_officialjournal_issn_electronic_and_more'))
        JournalURL = old_state.apps.get_model('journal', 'JournalURL')

        journal_url = JournalURL.objects.filter(journal=journal).first()
        self.assertIsNone(journal_url)

        migrator.reset()
