import unittest
from unittest.mock import patch

from django.contrib.auth import get_user_model

from institution.models import Institution


from journal.models import (
    SciELOJournal,
    Journal,
    OfficialJournal,
    Collection,
    Subject,
    Publisher,
    Copyright,
)

from journal.outputs.tabs_journal import (
    add_extraction_date,
    add_tabs_journal,
    add_issn_scielo,
    add_issns,
    add_title_at_scielo,
    add_title_thematic_areas,
    add_title_current_status,
    add_title_subtitle_scielo,
    add_short_title_scielo,
    add_publisher_name,
    add_use_license,
)

User = get_user_model()


class TabsJournalTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        user, created = User.objects.get_or_create(username="teste_user", password="teste_user")
        self.collection, created = Collection.objects.get_or_create(acron3="bol", creator=user)

        self.official_journal = OfficialJournal.create_or_update(
            user=user,
            title="Official Journal Title",
            issn_print="0000-0000",
            issn_electronic="1111-1111",
            issnl="2222-2222",
            foundation_year=None
        )
        self.journal = Journal.create_or_update(
            user=user,
            official_journal=self.official_journal,
            title="Journal Title",
            short_title="Journal Short Title",
            other_titles=None,
        )
        self.journal.subject.add(Subject.create_or_update(code="Health Sciences", user=user))
        self.journal.subject.add(Subject.create_or_update(code="Exact and Earth Sciences", user=user))

        for publ in ["Colegio Médico de La Paz", "Sociedad Boliviana de Pediatría"]:
            self.publisher = Publisher(page=self.journal)
            self.publisher.save()
            self.publisher.institution, created = Institution.objects.get_or_create(name=publ, creator=user)
            self.publisher.institution.save()
            self.publisher.save()

        self.scielo_journal = SciELOJournal.create_or_update(
            user=user,
            collection=self.collection,
            issn_scielo="0000-0000",
            journal=self.journal,
            journal_acron=None
        )
        self.scielo_journal.status = "Current"

    def tearDown(self):
        Publisher.objects.all().delete()

    @patch('journal.outputs.tabs_journal.get_date')
    def test_add_tabs_journal(self, mock_get_date):
        obtained = {}

        mock_get_date.return_value = "1900-01-01"

        add_extraction_date(obtained)

        add_tabs_journal(self.scielo_journal, collection="bol", dict_data=obtained)

        expected = {
            "extraction date": "1900-01-01",
            "study unit": "journal",
            "collection": "bol",
            "ISSN SciELO": "0000-0000",
            "ISSN's": "0000-0000;1111-1111;2222-2222",
            "title at SciELO": "Journal Title",
            "title thematic areas": "Health Sciences;Exact and Earth Sciences",
            "title is agricultural sciences": 0,
            "title is applied social sciences": 0,
            "title is biological sciences": 0,
            "title is engineering": 0,
            "title is exact and earth sciences": 1,
            "title is health sciences": 1,
            "title is human sciences": 0,
            "title is linguistics, letters and arts": 0,
            "title is multidisciplinary": 0,
            "title + subtitle SciELO": "Journal Title",
            "short title SciELO": "Journal Short Title",
            "publisher name": "Colegio Médico de La Paz; Sociedad Boliviana de Pediatría"
        }

        self.assertDictEqual(expected, obtained)

    @patch('journal.outputs.tabs_journal.get_date')
    def test_add_extraction_date(self, mock_get_date):
        obtained = {}

        mock_get_date.return_value = "1900-01-01"

        add_extraction_date(obtained)

        expected = {
            "extraction date": "1900-01-01"
        }

        self.assertDictEqual(expected, obtained)

    def test_add_issn_scielo(self):
        obtained = {}

        add_issn_scielo(self.scielo_journal, obtained)

        expected = {
            "ISSN SciELO": "0000-0000"
        }

        self.assertDictEqual(expected, obtained)

    def test_add_issns(self):
        obtained = {}

        add_issns(self.scielo_journal, obtained)

        expected = {
            "ISSN's": "0000-0000;1111-1111;2222-2222"
        }

        self.assertDictEqual(expected, obtained)

    def test_add_title_at_scielo(self):
        obtained = {}

        add_title_at_scielo(self.scielo_journal, obtained)

        expected = {
            "title at SciELO": "Journal Title"
        }

        self.assertDictEqual(expected, obtained)

    def test_add_title_current_status(self):
        obtained = {}

        add_title_current_status(self.scielo_journal, obtained)

        expected = {
            "title current status": "current"
        }

        self.assertDictEqual(expected, obtained)

    def test_add_title_thematic_areas(self):
        obtained = {}

        add_title_thematic_areas(self.scielo_journal, obtained)

        expected = {
            "title thematic areas": "Health Sciences;Exact and Earth Sciences",
            "title is agricultural sciences": 0,
            "title is applied social sciences": 0,
            "title is biological sciences": 0,
            "title is engineering": 0,
            "title is exact and earth sciences": 1,
            "title is health sciences": 1,
            "title is human sciences": 0,
            "title is linguistics, letters and arts": 0,
            "title is multidisciplinary": 0
        }

        self.assertDictEqual(expected, obtained)

    def test_add_title_subtitle_scielo(self):
        obtained = {}

        add_title_subtitle_scielo(self.scielo_journal, obtained)

        expected = {
            "title + subtitle SciELO": "Journal Title"
        }

        self.assertDictEqual(expected, obtained)

    def test_add_short_title_scielo(self):
        obtained = {}

        add_short_title_scielo(self.scielo_journal, obtained)

        expected = {
            "short title SciELO": "Journal Short Title"
        }

        self.assertDictEqual(expected, obtained)

    def test_add_publisher_name(self):
        obtained = {}

        add_publisher_name(self.scielo_journal, obtained)

        expected = {
            "publisher name": "Colegio Médico de La Paz; Sociedad Boliviana de Pediatría"
        }

        self.assertDictEqual(expected, obtained)


if __name__ == '__main__':
    unittest.main()
