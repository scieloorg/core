from django.test import TestCase

from core.users.models import User
from institution.models import (
    CopyrightHolder,
    Institution,
    InstitutionIdentification,
    Owner,
    Publisher,
    Sponsor,
)
from institution.tasks import task_delete_unlinked_institutions_and_locations
from journal.models import (
    CopyrightHolderHistory,
    Journal,
    OwnerHistory,
    PublisherHistory,
    SponsorHistory,
)
from location.models import City, Country, Location, State


class TaskDeleteUnlinkedInstitutionsAndLocationsTest(TestCase):
    """Tests for task_delete_unlinked_institutions_and_locations"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser")
        self.journal = Journal.objects.create(title="Test Journal")

        # Create Location with related objects
        self.country = Country.objects.create(
            name="Brazil", acronym="BR", acron3="BRA"
        )
        self.state = State.objects.create(name="São Paulo", acronym="SP")
        self.city = City.objects.create(name="Campinas")
        self.location = Location.objects.create(
            creator=self.user,
            country=self.country,
            state=self.state,
            city=self.city,
        )

        # Create InstitutionIdentification
        self.inst_id = InstitutionIdentification.objects.create(
            creator=self.user, name="Test Institution"
        )

        # Create Institution
        self.institution = Institution.objects.create(
            creator=self.user,
            institution_identification=self.inst_id,
            location=self.location,
        )

    def _create_linked_history(self, history_class, base_institution_class, **kwargs):
        """Helper to create a *History instance linked to an Institution."""
        base_inst = base_institution_class.objects.create(
            creator=self.user,
            institution=self.institution,
        )
        history = history_class.objects.create(
            journal=self.journal,
            institution=base_inst,
            creator=self.user,
            **kwargs,
        )
        return history, base_inst

    def test_history_with_raw_data_has_institution_set_to_none(self):
        """History instances with filled raw data should have institution set to None."""
        history, _ = self._create_linked_history(
            PublisherHistory,
            Publisher,
            raw_institution_name="Publisher Name",
        )
        self.assertIsNotNone(history.institution)

        task_delete_unlinked_institutions_and_locations()

        history.refresh_from_db()
        self.assertIsNone(history.institution)

    def test_history_without_raw_data_keeps_institution(self):
        """History instances without raw data should keep their institution link."""
        history, _ = self._create_linked_history(
            OwnerHistory,
            Owner,
        )
        self.assertIsNotNone(history.institution)

        task_delete_unlinked_institutions_and_locations()

        history.refresh_from_db()
        self.assertIsNotNone(history.institution)

    def test_institution_linked_to_history_not_deleted(self):
        """Institution linked to a *History (without raw data) should not be deleted."""
        self._create_linked_history(OwnerHistory, Owner)

        task_delete_unlinked_institutions_and_locations()

        self.assertTrue(
            Institution.objects.filter(pk=self.institution.pk).exists()
        )

    def test_institution_not_linked_to_history_is_deleted(self):
        """Institution not linked to any *History should be deleted."""
        task_delete_unlinked_institutions_and_locations()

        self.assertFalse(
            Institution.objects.filter(pk=self.institution.pk).exists()
        )

    def test_institution_fk_m2m_cleared_before_deletion(self):
        """Institution FK/M2M fields should be cleared before deletion."""
        # Create a second institution to survive and verify the first is deleted
        inst_id2 = InstitutionIdentification.objects.create(
            creator=self.user, name="Surviving Institution"
        )
        institution2 = Institution.objects.create(
            creator=self.user,
            institution_identification=inst_id2,
        )
        # Link institution2 to a history without raw data so it survives
        owner = Owner.objects.create(
            creator=self.user, institution=institution2
        )
        OwnerHistory.objects.create(
            journal=self.journal, institution=owner, creator=self.user
        )

        task_delete_unlinked_institutions_and_locations()

        # The first institution (unlinked) should be deleted
        self.assertFalse(
            Institution.objects.filter(pk=self.institution.pk).exists()
        )
        # The InstitutionIdentification should still exist (FK was cleared)
        self.assertTrue(
            InstitutionIdentification.objects.filter(pk=self.inst_id.pk).exists()
        )

    def test_institution_unlinked_after_raw_data_filled(self):
        """Institution becomes unlinked when all its *History instances have raw data."""
        self._create_linked_history(
            PublisherHistory,
            Publisher,
            raw_text="Some raw text",
        )

        task_delete_unlinked_institutions_and_locations()

        # After step 1, the history's institution is set to None,
        # so in step 2 the institution is no longer linked
        self.assertFalse(
            Institution.objects.filter(pk=self.institution.pk).exists()
        )

    def test_all_locations_deleted(self):
        """All Location instances should be deleted."""
        task_delete_unlinked_institutions_and_locations()

        self.assertEqual(Location.objects.count(), 0)

    def test_location_fk_cleared_before_deletion(self):
        """Location FK fields are cleared before deletion."""
        task_delete_unlinked_institutions_and_locations()

        # Location is deleted
        self.assertEqual(Location.objects.count(), 0)
        # Country, State, City still exist (FK was cleared before deletion)
        self.assertTrue(Country.objects.filter(pk=self.country.pk).exists())
        self.assertTrue(State.objects.filter(pk=self.state.pk).exists())
        self.assertTrue(City.objects.filter(pk=self.city.pk).exists())

    def test_multiple_history_classes(self):
        """Test with multiple history classes simultaneously."""
        # Publisher with raw data
        pub_history, _ = self._create_linked_history(
            PublisherHistory,
            Publisher,
            raw_country_code="BR",
        )
        # Sponsor without raw data (linked)
        spn_history, _ = self._create_linked_history(
            SponsorHistory,
            Sponsor,
        )
        # CopyrightHolder with raw data
        ch_history, _ = self._create_linked_history(
            CopyrightHolderHistory,
            CopyrightHolder,
            raw_city_name="São Paulo",
        )

        task_delete_unlinked_institutions_and_locations()

        pub_history.refresh_from_db()
        spn_history.refresh_from_db()
        ch_history.refresh_from_db()

        # Publisher and CopyrightHolder had raw data → institution = None
        self.assertIsNone(pub_history.institution)
        self.assertIsNone(ch_history.institution)
        # Sponsor had no raw data → institution kept
        self.assertIsNotNone(spn_history.institution)

    def test_task_returns_counts(self):
        """Task should return counts of deleted objects."""
        result = task_delete_unlinked_institutions_and_locations()

        self.assertIn("deleted_institutions", result)
        self.assertIn("deleted_locations", result)
        self.assertEqual(result["deleted_institutions"], 1)
        self.assertEqual(result["deleted_locations"], 1)
