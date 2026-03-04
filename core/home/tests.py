from unittest.mock import patch

from django.test import TestCase

from collection.models import Collection
from core.users.models import User
from journal.models import Journal, SciELOJournal

from core.home.views import _get_scielo_journals_data


class TestGetScieloJournalsData(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser", password="testpass")
        self.collection = Collection.objects.create(
            creator=self.user,
            acron3="per",
            domain="http://www.scielo.org.pe",
        )
        self.journal = Journal.objects.create(
            creator=self.user,
            title="Test Journal Peru",
        )
        self.scielo_journal = SciELOJournal.objects.create(
            issn_scielo="2709-3689",
            collection=self.collection,
            journal=self.journal,
            journal_acron="tjperu",
        )

    def test_scielo_url_does_not_have_double_http_prefix(self):
        """URL must not contain 'http://http://' when domain already has http://"""
        data = _get_scielo_journals_data()
        self.assertTrue(len(data) > 0)
        for item in data:
            self.assertNotIn("http://http://", item["scielo_url"])
            self.assertNotIn("http://https://", item["scielo_url"])

    def test_scielo_url_is_well_formed(self):
        """URL must be a valid scielo.php URL with the correct domain"""
        data = _get_scielo_journals_data()
        self.assertEqual(len(data), 1)
        expected_url = (
            "http://www.scielo.org.pe/scielo.php?script=sci_serial"
            "&pid=2709-3689&lng=en"
        )
        self.assertEqual(data[0]["scielo_url"], expected_url)

    def test_scielo_url_strips_trailing_slash_from_domain(self):
        """Trailing slash in domain must not produce double slash in URL"""
        self.collection.domain = "http://www.scielo.org.pe/"
        self.collection.save()
        data = _get_scielo_journals_data()
        self.assertEqual(len(data), 1)
        self.assertNotIn("//scielo.php", data[0]["scielo_url"])

    def test_scielo_url_with_https_domain(self):
        """URL must be correct when domain uses https://"""
        self.collection.domain = "https://www.scielo.br"
        self.collection.save()
        data = _get_scielo_journals_data()
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["scielo_url"].startswith("https://www.scielo.br/"))
        self.assertNotIn("https://https://", data[0]["scielo_url"])
