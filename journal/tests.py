import json
from unittest.mock import patch
from deepdiff import DeepDiff
from django.test import TestCase
from django_test_migrations.migrator import Migrator

from collection.models import Collection
from core.models import Gender, Language, License
from core.users.models import User
from editorialboard.models import RoleModel
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
    fetch_and_process_journal_logos_in_collection,
    load_license_of_use_in_journal,
)
from journal.formats.articlemeta_format import get_articlemeta_format_title
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


class TestFetchAndProcessJournalLogosInCollection(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.collection = Collection.objects.create(
            creator=self.user, acron3="scl", is_active=True
        )
        self.journal = Journal.objects.create(creator=self.user, title="Test Journal")
        self.scielo_journal = SciELOJournal.objects.create(
            issn_scielo="1516-635X",
            collection=self.collection,
            journal=self.journal,
            journal_acron="abdc",
        )

    def test_fetch_and_process_journal_logos_with_invalid_collection(self):
        """Test that ValueError is raised when collection does not exist"""
        with self.assertRaises(ValueError) as context:
            fetch_and_process_journal_logos_in_collection(
                collection_acron3="invalid_acron",
                username=self.user.username,
            )
        self.assertIn("does not exist", str(context.exception))

    @patch("journal.tasks.group")
    def test_fetch_and_process_journal_logos_with_valid_collection(self, mock_group):
        """Test that task executes with valid collection"""
        # Mock the group to avoid actually running the celery tasks
        mock_group.return_value.return_value = None
        
        result = fetch_and_process_journal_logos_in_collection(
            collection_acron3=self.collection.acron3,
            username=self.user.username,
        )
        
        # The task should complete without raising an exception
        # and should call group with the task signatures
        self.assertTrue(mock_group.called)


class RawOrganizationMixinTestCase(TestCase):
    """Test cases for RawOrganizationMixin functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(username="testuser")
        self.collection = Collection.objects.create(
            name="Test Collection",
            acron3="TST",
        )
        self.journal = Journal.objects.create(
            title="Test Journal",
        )

    def test_add_publisher_with_raw_organization_fields(self):
        """Test that add_publisher accepts and saves raw organization fields"""
        publisher_history = self.journal.add_publisher(
            user=self.user,
            original_data="Test Publisher",
            raw_institution_name="Test Publisher Inc.",
            raw_country_name="Brazil",
            raw_country_code="BR",
            raw_state_name="São Paulo",
            raw_state_acron="SP",
            raw_city_name="São Paulo",
        )
        
        self.assertIsNotNone(publisher_history)
        self.assertEqual(publisher_history.raw_institution_name, "Test Publisher Inc.")
        self.assertEqual(publisher_history.raw_country_name, "Brazil")
        self.assertEqual(publisher_history.raw_country_code, "BR")
        self.assertEqual(publisher_history.raw_state_name, "São Paulo")
        self.assertEqual(publisher_history.raw_state_acron, "SP")
        self.assertEqual(publisher_history.raw_city_name, "São Paulo")

    def test_add_owner_with_raw_organization_fields(self):
        """Test that add_owner accepts and saves raw organization fields"""
        owner_history = self.journal.add_owner(
            user=self.user,
            original_data="Test Owner",
            raw_institution_name="Test Owner Institution",
            raw_country_name="Argentina",
        )
        
        self.assertIsNotNone(owner_history)
        self.assertEqual(owner_history.raw_institution_name, "Test Owner Institution")
        self.assertEqual(owner_history.raw_country_name, "Argentina")

    def test_add_sponsor_with_raw_organization_fields(self):
        """Test that add_sponsor accepts and saves raw organization fields"""
        sponsor_history = self.journal.add_sponsor(
            user=self.user,
            original_data="Test Sponsor",
            raw_institution_name="Test Sponsor Foundation",
        )
        
        self.assertIsNotNone(sponsor_history)
        self.assertEqual(sponsor_history.raw_institution_name, "Test Sponsor Foundation")

    def test_add_copyright_holder_with_raw_organization_fields(self):
        """Test that add_copyright_holder accepts and saves raw organization fields"""
        copyright_history = self.journal.add_copyright_holder(
            user=self.user,
            original_data="Test Copyright Holder",
            raw_institution_name="Test Copyright Holder Corp",
            raw_text="Full copyright text",
        )
        
        self.assertIsNotNone(copyright_history)
        self.assertEqual(copyright_history.raw_institution_name, "Test Copyright Holder Corp")
        self.assertEqual(copyright_history.raw_text, "Full copyright text")

    def test_backward_compatibility_without_raw_fields(self):
        """Test that existing code without raw fields still works"""
        # This tests backward compatibility
        publisher_history = self.journal.add_publisher(
            user=self.user,
            original_data="Legacy Publisher",
        )
        
        self.assertIsNotNone(publisher_history)
        # Raw fields should be None if not provided
        self.assertIsNone(publisher_history.raw_institution_name)
        self.assertIsNone(publisher_history.raw_country_name)


class MigrateInstitutionDataToRawInstitutionTestCase(TestCase):
    """Test cases for migrate_institution_data_to_raw_institution task"""

    def setUp(self):
        """Set up test fixtures"""
        from institution.models import (
            Institution,
            InstitutionIdentification,
            Publisher,
            Owner,
            Sponsor,
            CopyrightHolder,
        )
        from location.models import City, State, Country, Location
        from journal.models import (
            PublisherHistory,
            OwnerHistory,
            SponsorHistory,
            CopyrightHolderHistory,
        )
        
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.journal = Journal.objects.create(
            title="Test Journal",
            creator=self.user,
        )
        
        # Create country, state, and city
        self.country = Country.objects.create(
            name="Brazil",
            acron3="BRA",
        )
        self.state = State.objects.create(
            name="São Paulo",
            acronym="SP",
            region="Southeast",
        )
        self.city = City.objects.create(
            name="São Paulo",
            state=self.state,
        )
        self.location = Location.objects.create(
            country=self.country,
            state=self.state,
            city=self.city,
        )
        
        # Create institution identification
        self.institution_identification = InstitutionIdentification.objects.create(
            name="Test University",
            acronym="TU",
            creator=self.user,
        )
        
        # Create institution
        self.institution = Institution.objects.create(
            institution_identification=self.institution_identification,
            location=self.location,
            level_1="Faculty of Science",
            level_2="Department of Physics",
            level_3="Research Lab",
            creator=self.user,
        )
        
        # Create Publisher, Owner, Sponsor, CopyrightHolder
        self.publisher = Publisher.objects.create(
            institution=self.institution,
            creator=self.user,
        )
        self.owner = Owner.objects.create(
            institution=self.institution,
            creator=self.user,
        )
        self.sponsor = Sponsor.objects.create(
            institution=self.institution,
            creator=self.user,
        )
        self.copyright_holder = CopyrightHolder.objects.create(
            institution=self.institution,
            creator=self.user,
        )
        
        # Create History records with institution
        self.publisher_history = PublisherHistory.objects.create(
            journal=self.journal,
            institution=self.publisher,
            initial_date="2020-01-01",
            creator=self.user,
        )
        self.owner_history = OwnerHistory.objects.create(
            journal=self.journal,
            institution=self.owner,
            initial_date="2020-01-01",
            creator=self.user,
        )
        self.sponsor_history = SponsorHistory.objects.create(
            journal=self.journal,
            institution=self.sponsor,
            initial_date="2020-01-01",
            creator=self.user,
        )
        self.copyright_holder_history = CopyrightHolderHistory.objects.create(
            journal=self.journal,
            institution=self.copyright_holder,
            initial_date="2020-01-01",
            creator=self.user,
        )

    def test_migrate_publisher_history(self):
        """Test migration of PublisherHistory institution data to raw fields"""
        from journal.tasks import migrate_institution_data_to_raw_institution
        
        # Run the migration task
        result = migrate_institution_data_to_raw_institution(
            username=self.user.username,
        )
        
        # Verify the result
        self.assertEqual(result["PublisherHistory"]["migrated"], 1)
        self.assertEqual(result["PublisherHistory"]["errors"], 0)
        
        # Refresh the record from database
        self.publisher_history.refresh_from_db()
        
        # Verify that institution is None
        self.assertIsNone(self.publisher_history.institution)
        
        # Verify that raw fields are populated
        self.assertEqual(self.publisher_history.raw_institution_name, "Test University")
        self.assertEqual(self.publisher_history.raw_country_name, "Brazil")
        self.assertEqual(self.publisher_history.raw_country_code, "BRA")
        self.assertEqual(self.publisher_history.raw_state_name, "São Paulo")
        self.assertEqual(self.publisher_history.raw_state_acron, "SP")
        self.assertEqual(self.publisher_history.raw_city_name, "São Paulo")
        
        # Verify raw_text
        expected_text = "Test University | (TU) | Faculty of Science | Department of Physics | Research Lab"
        self.assertEqual(self.publisher_history.raw_text, expected_text)

    def test_migrate_owner_history(self):
        """Test migration of OwnerHistory institution data to raw fields"""
        from journal.tasks import migrate_institution_data_to_raw_institution
        
        # Run the migration task
        result = migrate_institution_data_to_raw_institution(
            username=self.user.username,
        )
        
        # Verify the result
        self.assertEqual(result["OwnerHistory"]["migrated"], 1)
        self.assertEqual(result["OwnerHistory"]["errors"], 0)
        
        # Refresh the record from database
        self.owner_history.refresh_from_db()
        
        # Verify that institution is None
        self.assertIsNone(self.owner_history.institution)
        
        # Verify that raw fields are populated
        self.assertEqual(self.owner_history.raw_institution_name, "Test University")
        self.assertEqual(self.owner_history.raw_country_name, "Brazil")

    def test_migrate_sponsor_history(self):
        """Test migration of SponsorHistory institution data to raw fields"""
        from journal.tasks import migrate_institution_data_to_raw_institution
        
        # Run the migration task
        result = migrate_institution_data_to_raw_institution(
            username=self.user.username,
        )
        
        # Verify the result
        self.assertEqual(result["SponsorHistory"]["migrated"], 1)
        self.assertEqual(result["SponsorHistory"]["errors"], 0)
        
        # Refresh the record from database
        self.sponsor_history.refresh_from_db()
        
        # Verify that institution is None
        self.assertIsNone(self.sponsor_history.institution)
        
        # Verify that raw fields are populated
        self.assertEqual(self.sponsor_history.raw_institution_name, "Test University")

    def test_migrate_copyright_holder_history(self):
        """Test migration of CopyrightHolderHistory institution data to raw fields"""
        from journal.tasks import migrate_institution_data_to_raw_institution
        
        # Run the migration task
        result = migrate_institution_data_to_raw_institution(
            username=self.user.username,
        )
        
        # Verify the result
        self.assertEqual(result["CopyrightHolderHistory"]["migrated"], 1)
        self.assertEqual(result["CopyrightHolderHistory"]["errors"], 0)
        
        # Refresh the record from database
        self.copyright_holder_history.refresh_from_db()
        
        # Verify that institution is None
        self.assertIsNone(self.copyright_holder_history.institution)
        
        # Verify that raw fields are populated
        self.assertEqual(self.copyright_holder_history.raw_institution_name, "Test University")

    def test_migrate_all_history_models(self):
        """Test that all four history models are migrated"""
        from journal.tasks import migrate_institution_data_to_raw_institution
        
        # Run the migration task
        result = migrate_institution_data_to_raw_institution(
            username=self.user.username,
        )
        
        # Verify that all models were processed
        self.assertIn("PublisherHistory", result)
        self.assertIn("OwnerHistory", result)
        self.assertIn("SponsorHistory", result)
        self.assertIn("CopyrightHolderHistory", result)
        
        # Verify that all records were migrated
        self.assertEqual(result["PublisherHistory"]["migrated"], 1)
        self.assertEqual(result["OwnerHistory"]["migrated"], 1)
        self.assertEqual(result["SponsorHistory"]["migrated"], 1)
        self.assertEqual(result["CopyrightHolderHistory"]["migrated"], 1)

    def test_migrate_with_partial_institution_data(self):
        """Test migration when institution has partial data"""
        from institution.models import Institution, InstitutionIdentification
        from journal.models import PublisherHistory
        from institution.models import Publisher
        
        # Create institution with only name, no location
        institution_id = InstitutionIdentification.objects.create(
            name="Simple Institution",
            creator=self.user,
        )
        institution = Institution.objects.create(
            institution_identification=institution_id,
            creator=self.user,
        )
        publisher = Publisher.objects.create(
            institution=institution,
            creator=self.user,
        )
        
        # Create history record
        publisher_history = PublisherHistory.objects.create(
            journal=self.journal,
            institution=publisher,
            initial_date="2021-01-01",
            creator=self.user,
        )
        
        # Run migration
        from journal.tasks import migrate_institution_data_to_raw_institution
        result = migrate_institution_data_to_raw_institution(
            username=self.user.username,
        )
        
        # Verify that records were migrated (2 for this test + 1 from setUp)
        self.assertEqual(result["PublisherHistory"]["migrated"], 2)
        
        # Refresh and verify
        publisher_history.refresh_from_db()
        self.assertIsNone(publisher_history.institution)
        self.assertEqual(publisher_history.raw_institution_name, "Simple Institution")
        # Location fields should be None
        self.assertIsNone(publisher_history.raw_country_name)
        self.assertIsNone(publisher_history.raw_city_name)

    def test_migrate_history_without_institution(self):
        """Test that migration skips history records without institution"""
        from journal.models import PublisherHistory
        
        # Create history record without institution
        publisher_history = PublisherHistory.objects.create(
            journal=self.journal,
            initial_date="2022-01-01",
            creator=self.user,
        )
        
        # Run migration
        from journal.tasks import migrate_institution_data_to_raw_institution
        result = migrate_institution_data_to_raw_institution(
            username=self.user.username,
        )
        
        # The migration should process existing records with institution
        # but skip the one without institution
        # Verify that the new record still has institution=None and no raw data
        publisher_history.refresh_from_db()
        self.assertIsNone(publisher_history.institution)
        self.assertIsNone(publisher_history.raw_institution_name)

