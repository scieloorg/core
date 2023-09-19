import unittest

from journal.models import (
    SciELOJournal,
    Journal,
    Collection,
)

from journal.outputs.tabs_journal import (
    get_tabs_journal,
    get_issn_scielo,
    get_collection,
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

