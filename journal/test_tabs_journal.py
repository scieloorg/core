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
        self.col = Collection()
        self.col.acron3 = "bol"
        self.col.save()

        self.jnl = Journal()
        self.jnl.save()
        self.jnl.collection.add(self.col)
        self.jnl.save()

        self.scl = SciELOJournal()
        self.scl.issn_scielo = "0000-0000"
        self.scl.save()
        self.scl.journal = self.jnl
        self.scl.collection = self.col
        self.scl.save()

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
