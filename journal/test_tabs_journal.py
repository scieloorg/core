import unittest
from unittest.mock import patch

from journal.models import (
    SciELOJournal,
    Journal,
    OfficialJournal,
)

from journal.outputs.tabs_journal import (
    add_extraction_date,
    add_tabs_journal,
    add_issn_scielo,
    add_issns,
)


class TabsJournalTest(unittest.TestCase):
    def setUp(self):
        self.official_journal = OfficialJournal.objects.create(
            issn_print="0000-0000",
            issn_electronic="1111-1111",
            issnl="2222-2222",
        )

        self.journal = Journal.objects.create(
            official=self.official_journal,
        )

        self.scielo_journal = SciELOJournal.objects.create(
            issn_scielo="0000-0000",
            journal=self.journal,
        )

    def test_get_tabs_journal(self):
        obtained = {}

        get_tabs_journal(self.scl, obtained)

        expected = {
            "ISSN SciELO": "0000-0000",
            "collection": "bol"
        }

        self.assertDictEqual(expected, obtained)

    def test_get_issn_scielo(self):
        obtained = {}

        get_issn_scielo(self.scl, obtained)

        expected = {
            "ISSN SciELO": "0000-0000"
        }

        self.assertDictEqual(expected, obtained)

    def test_get_collection(self):
        obtained = {}

        get_collection(self.scl, obtained)

        expected = {
            "collection": "bol"
        }

        self.assertDictEqual(expected, obtained)


if __name__ == '__main__':
    unittest.main()
