from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from collection.models import Collection
from core.users.models import User
from journal.models import Journal, SciELOJournal, Subject

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
            status="C",
        )
        self.factory = RequestFactory()

    def test_as_export_dict_returns_title_url_and_owner(self):
        data = self.scielo_journal.as_export_dict()
        self.assertEqual(data["title"], "Test Journal Peru")
        self.assertEqual(
            data["scielo_url"],
            "http://www.scielo.org.pe/scielo.php?script=sci_serial"
            "&pid=2709-3689&lng=en",
        )
        self.assertEqual(data["owner"], "")

    def test_scielo_url_is_empty_when_collection_has_no_domain(self):
        self.collection.domain = None
        self.collection.save()
        self.assertEqual(self.scielo_journal.scielo_url, "")

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

    def test_journal_without_domain_does_not_drop_other_journals(self):
        collection_without_domain = Collection.objects.create(
            creator=self.user,
            acron3="xyz",
            domain=None,
        )
        journal_without_domain = Journal.objects.create(
            creator=self.user,
            title="Journal Without Domain",
        )
        SciELOJournal.objects.create(
            issn_scielo="1111-1111",
            collection=collection_without_domain,
            journal=journal_without_domain,
            journal_acron="tjnodomain",
            status="C",
        )
        data = _get_scielo_journals_data()
        titles = [item["title"] for item in data]
        self.assertIn("Test Journal Peru", titles)
        self.assertIn("Journal Without Domain", titles)
        empty_url_item = next(
            item for item in data if item["title"] == "Journal Without Domain"
        )
        self.assertEqual(empty_url_item["scielo_url"], "")

    def test_category_filter_returns_only_journals_from_that_category(self):
        health = Subject.objects.create(
            creator=self.user,
            code="Health Sciences",
            value="Health Sciences",
        )
        engineering = Subject.objects.create(
            creator=self.user,
            code="Engineering",
            value="Engineering",
        )
        self.journal.subject.add(health)

        engineering_journal = Journal.objects.create(
            creator=self.user,
            title="Engineering Journal",
        )
        engineering_journal.subject.add(engineering)
        SciELOJournal.objects.create(
            issn_scielo="2222-2222",
            collection=self.collection,
            journal=engineering_journal,
            journal_acron="tjeng",
            status="C",
        )

        request = self.factory.get(
            "/download-csv-journals-page-scielo-org/",
            {"category": "health-sciences"},
        )
        data = _get_scielo_journals_data(request)
        titles = [item["title"] for item in data]
        self.assertEqual(titles, ["Test Journal Peru"])

    def test_csv_download_contains_journal_rows(self):
        response = self.client.get(reverse("download_csv_journals_page_scielo_org"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("journals,scielo_url,publisher", content)
        self.assertIn("Test Journal Peru", content)

    def test_xls_download_contains_journal_rows(self):
        response = self.client.get(reverse("download_xls_journals_page_scielo_org"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test Journal Peru", response.content.decode("latin-1", errors="ignore"))

    def test_csv_download_filters_by_category(self):
        health = Subject.objects.create(
            creator=self.user,
            code="Health Sciences",
            value="Health Sciences",
        )
        self.journal.subject.add(health)
        other_journal = Journal.objects.create(
            creator=self.user,
            title="Other Journal",
        )
        SciELOJournal.objects.create(
            issn_scielo="3333-3333",
            collection=self.collection,
            journal=other_journal,
            journal_acron="tjother",
            status="C",
        )

        response = self.client.get(
            reverse("download_csv_journals_page_scielo_org"),
            {"category": "health-sciences"},
        )
        content = response.content.decode("utf-8")
        self.assertIn("Test Journal Peru", content)
        self.assertNotIn("Other Journal", content)
        date = timezone.now().strftime("%Y-%m-%d")
        self.assertIn(
            f'filename="health-sciences_{date}.csv"',
            response["Content-Disposition"],
        )

    def test_csv_download_filename_uses_all_journals_without_category(self):
        response = self.client.get(reverse("download_csv_journals_page_scielo_org"))
        date = timezone.now().strftime("%Y-%m-%d")
        self.assertIn(
            f'filename="all_journals_{date}.csv"',
            response["Content-Disposition"],
        )

    def test_xls_download_filename_uses_category_when_present(self):
        response = self.client.get(
            reverse("download_xls_journals_page_scielo_org"),
            {"category": "health-sciences"},
        )
        date = timezone.now().strftime("%Y-%m-%d")
        self.assertIn(
            f'filename="health-sciences_{date}.xls"',
            response["Content-Disposition"],
        )
