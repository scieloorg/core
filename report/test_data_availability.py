from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from article import choices
from article.models import Article
from collection.models import Collection
from issue.models import Issue
from journal.models import Journal, SciELOJournal
from report import data_availability
from report.forms import DataAvailabilityFilterForm
from report.views import PUBLIC_REPORTS

User = get_user_model()

NOT_PROCESSED = choices.DATA_AVAILABILITY_STATUS_NOT_PROCESSED


class DataAvailabilityDataMixin:
    """
    Artigos:
        1. data-available, fascículo 2023, online 2022, periódico X (coleções scl e arg)
        2. absent,         fascículo 2023, online 2023, periódico X (coleções scl e arg)
        3. data-available, fascículo 2024, online 2023, periódico Y (coleção scl)
        4. not-processed,  fascículo 2024, online 2024, periódico Z (coleção arg)
        5. data-available, fascículo 2024, online 2024, periódico Z, DELETED (ignorado)
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="das-report-user", password="x")
        cls.col_scl = Collection.objects.create(acron3="scl", creator=cls.user)
        cls.col_arg = Collection.objects.create(acron3="arg", creator=cls.user)
        cls.journal_x = Journal.objects.create(title="Journal X", creator=cls.user)
        cls.journal_y = Journal.objects.create(title="Journal Y", creator=cls.user)
        cls.journal_z = Journal.objects.create(title="Journal Z", creator=cls.user)
        for journal, collections in (
            (cls.journal_x, [cls.col_scl, cls.col_arg]),
            (cls.journal_y, [cls.col_scl]),
            (cls.journal_z, [cls.col_arg]),
        ):
            for collection in collections:
                SciELOJournal.objects.create(
                    journal=journal,
                    collection=collection,
                    journal_acron=journal.title[-1].lower(),
                    creator=cls.user,
                )
        cls.issue_2023 = Issue.objects.create(year="2023", creator=cls.user)
        cls.issue_2024 = Issue.objects.create(year="2024", creator=cls.user)

        def make(pid, status, issue, pub_year, journal, data_status=None):
            return Article.objects.create(
                pid_v3=pid,
                creator=cls.user,
                issue=issue,
                journal=journal,
                pub_date_year=pub_year,
                data_availability_status=status,
                data_status=data_status or choices.DATA_STATUS_PUBLIC,
            )

        cls.articles = [
            make("das-1", choices.DATA_AVAILABILITY_STATUS_AVAILABLE, cls.issue_2023, "2022", cls.journal_x),
            make("das-2", choices.DATA_AVAILABILITY_STATUS_ABSENT, cls.issue_2023, "2023", cls.journal_x),
            make("das-3", choices.DATA_AVAILABILITY_STATUS_AVAILABLE, cls.issue_2024, "2023", cls.journal_y),
            make("das-4", NOT_PROCESSED, cls.issue_2024, "2024", cls.journal_z),
            make(
                "das-5",
                choices.DATA_AVAILABILITY_STATUS_AVAILABLE,
                cls.issue_2024,
                "2024",
                cls.journal_z,
                data_status=choices.DATA_STATUS_DELETED,
            ),
        ]

    def setUp(self):
        cache.clear()

    @staticmethod
    def cell(row, status):
        return next(c for c in row["cells"] if c["status"] == status)


class PercentTest(TestCase):
    def test_percent(self):
        self.assertEqual(33.33, data_availability.percent(1, 3))

    def test_zero_total(self):
        self.assertEqual(0, data_availability.percent(0, 0))


class BuildReportTest(DataAvailabilityDataMixin, TestCase):
    def test_group_by_issue_year(self):
        report = data_availability.build_report(data_availability.filter_articles())
        self.assertEqual(["2024", "2023"], [r["year"] for r in report["rows"]])

        row_2023 = report["rows"][1]
        self.assertEqual(2, row_2023["total"])
        available = self.cell(row_2023, choices.DATA_AVAILABILITY_STATUS_AVAILABLE)
        self.assertEqual(1, available["count"])
        self.assertEqual(50, available["percent"])
        self.assertEqual(
            50, self.cell(row_2023, choices.DATA_AVAILABILITY_STATUS_ABSENT)["percent"]
        )
        self.assertEqual(1, self.cell(report["rows"][0], NOT_PROCESSED)["count"])

    def test_excludes_deleted_articles(self):
        report = data_availability.build_report(data_availability.filter_articles())
        self.assertEqual(4, report["totals"]["total"])

    def test_totals(self):
        totals = data_availability.build_report(
            data_availability.filter_articles()
        )["totals"]
        available = self.cell(totals, choices.DATA_AVAILABILITY_STATUS_AVAILABLE)
        self.assertEqual(2, available["count"])
        self.assertEqual(50, available["percent"])
        self.assertEqual(25, self.cell(totals, NOT_PROCESSED)["percent"])
        self.assertEqual(
            0, self.cell(totals, choices.DATA_AVAILABILITY_STATUS_INVALID)["count"]
        )

    def test_columns_follow_choices(self):
        report = data_availability.build_report(data_availability.filter_articles())
        self.assertEqual(
            [status for status, _label in choices.DATA_AVAILABILITY_STATUS],
            [cell["status"] for cell in report["totals"]["cells"]],
        )

    def test_null_status_counts_as_not_processed(self):
        Article.objects.filter(pk=self.articles[3].pk).update(
            data_availability_status=None
        )
        totals = data_availability.build_report(
            data_availability.filter_articles()
        )["totals"]
        self.assertEqual(1, self.cell(totals, NOT_PROCESSED)["count"])

    def test_group_by_pub_year(self):
        report = data_availability.build_report(
            data_availability.filter_articles(),
            group_by=data_availability.GROUP_BY_PUB_YEAR,
        )
        self.assertEqual(
            ["2024", "2023", "2022"], [r["year"] for r in report["rows"]]
        )
        self.assertEqual(2, report["rows"][1]["total"])

    def test_without_year_goes_last(self):
        Article.objects.filter(pk=self.articles[0].pk).update(issue=None)
        report = data_availability.build_report(data_availability.filter_articles())
        self.assertEqual(["2024", "2023", None], [r["year"] for r in report["rows"]])

    def test_collection_does_not_duplicate(self):
        report = data_availability.build_report(
            data_availability.filter_articles(collection=self.col_scl)
        )
        self.assertEqual(3, report["totals"]["total"])

    def test_journal(self):
        report = data_availability.build_report(
            data_availability.filter_articles(journal=self.journal_z)
        )
        self.assertEqual(1, report["totals"]["total"])

    def test_pub_year_range_is_independent_of_issue_year(self):
        report = data_availability.build_report(
            data_availability.filter_articles(year_from="2023", year_to="2023")
        )
        self.assertEqual(2, report["totals"]["total"])
        self.assertEqual(["2024", "2023"], [r["year"] for r in report["rows"]])

    def test_empty(self):
        report = data_availability.build_report(Article.objects.none())
        self.assertEqual([], report["rows"])
        self.assertEqual(0, report["totals"]["total"])


class FilterOptionsTest(DataAvailabilityDataMixin, TestCase):
    def test_journals_all(self):
        titles = [j.title for j in data_availability.journals_for()]
        for title in ("Journal X", "Journal Y", "Journal Z"):
            self.assertIn(title, titles)

    def test_journals_by_collection(self):
        self.assertEqual(
            ["Journal X", "Journal Y"],
            [j.title for j in data_availability.journals_for(self.col_scl)],
        )
        self.assertEqual(
            ["Journal X", "Journal Z"],
            [j.title for j in data_availability.journals_for(self.col_arg)],
        )

    def test_pub_years(self):
        self.assertEqual(["2024", "2023", "2022"], data_availability.pub_years_for())
        self.assertEqual(
            ["2023", "2022"], data_availability.pub_years_for(self.col_scl)
        )
        self.assertEqual(
            ["2023", "2022"],
            data_availability.pub_years_for(self.col_arg, self.journal_x),
        )

    def test_filter_options(self):
        options = data_availability.filter_options(self.col_arg, self.journal_z)
        self.assertEqual(
            [
                {"id": self.journal_x.pk, "label": "Journal X"},
                {"id": self.journal_z.pk, "label": "Journal Z"},
            ],
            options["journals"],
        )
        self.assertEqual(["2024"], options["years"])


class DataAvailabilityFilterFormTest(DataAvailabilityDataMixin, TestCase):
    def test_valid(self):
        filters = DataAvailabilityFilterForm(
            {
                "collection": self.col_scl.pk,
                "journal": self.journal_x.pk,
                "year_from": "2022",
                "year_to": "2023",
                "group_by": data_availability.GROUP_BY_PUB_YEAR,
            }
        ).filters()
        self.assertEqual(self.col_scl, filters["collection"])
        self.assertEqual(self.journal_x, filters["journal"])
        self.assertEqual("2022", filters["year_from"])
        self.assertEqual(data_availability.GROUP_BY_PUB_YEAR, filters["group_by"])

    def test_invalid_fields_are_ignored(self):
        filters = DataAvailabilityFilterForm(
            {
                "collection": self.col_scl.pk,
                "journal": "abc",
                "year_from": "20x",
                "group_by": "x",
            }
        ).filters()
        self.assertEqual(self.col_scl, filters["collection"])
        self.assertIsNone(filters["journal"])
        self.assertIsNone(filters["year_from"])
        self.assertEqual(data_availability.GROUP_BY_ISSUE_YEAR, filters["group_by"])


class DataAvailabilityViewTest(DataAvailabilityDataMixin, TestCase):
    def url(self):
        return reverse("report_data_availability")

    def test_is_public(self):
        response = self.client.get(self.url())
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "report/data_availability.html")
        self.assertEqual(4, response.context["report"]["totals"]["total"])

    def test_filters(self):
        response = self.client.get(
            self.url(),
            {
                "collection": self.col_scl.pk,
                "year_from": "2023",
                "year_to": "2023",
                "group_by": data_availability.GROUP_BY_PUB_YEAR,
            },
        )
        report = response.context["report"]
        self.assertEqual(2, report["totals"]["total"])
        self.assertEqual(["2023"], [r["year"] for r in report["rows"]])
        self.assertEqual(
            ["Journal X", "Journal Y"], [j.title for j in response.context["journals"]]
        )
        self.assertEqual(["2023", "2022"], response.context["years"])

    def test_invalid_params(self):
        response = self.client.get(
            self.url(), {"journal": "abc", "year_from": "x", "group_by": "x"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(4, response.context["report"]["totals"]["total"])

    def test_empty_result(self):
        response = self.client.get(self.url(), {"year_from": "2099"})
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'class="empty"')

    def test_csv(self):
        response = self.client.get(self.url(), {"format": "csv"})
        self.assertEqual(200, response.status_code)
        self.assertIn("text/csv", response["Content-Type"])
        lines = response.content.decode().strip().splitlines()
        self.assertTrue(lines[0].startswith("year;total;data-available;"))
        self.assertTrue(lines[1].startswith("2024;2;"))
        self.assertTrue(lines[-1].startswith("total;4;"))

    def test_csv_link_does_not_repeat_format(self):
        response = self.client.get(self.url(), {"year_from": "2023"})
        self.assertEqual("year_from=2023", response.context["query_string"])

    def test_options_url_in_page(self):
        response = self.client.get(self.url())
        self.assertContains(
            response,
            f'data-options-url="{reverse("report_data_availability_options")}"',
        )


class DataAvailabilityOptionsViewTest(DataAvailabilityDataMixin, TestCase):
    def url(self):
        return reverse("report_data_availability_options")

    def test_is_public_json(self):
        response = self.client.get(self.url())
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/json", response["Content-Type"])
        self.assertEqual(["2024", "2023", "2022"], response.json()["years"])

    def test_collection_and_journal(self):
        data = self.client.get(
            self.url(), {"collection": self.col_scl.pk, "journal": self.journal_y.pk}
        ).json()
        self.assertEqual(
            ["Journal X", "Journal Y"], [j["label"] for j in data["journals"]]
        )
        self.assertEqual(["2023"], data["years"])


class ReportIndexViewTest(TestCase):
    def test_is_public(self):
        response = self.client.get(reverse("report_index"))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "report/index.html")

    def test_unprefixed_url_redirects_to_language(self):
        response = self.client.get("/report/", follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "report/index.html")

    def test_lists_all_reports(self):
        response = self.client.get(reverse("report_index"))
        for report in PUBLIC_REPORTS:
            self.assertContains(response, f'href="{reverse(report["url_name"])}"')
            self.assertContains(response, str(report["title"]))

    def test_report_page_links_back_to_index(self):
        cache.clear()
        response = self.client.get(reverse("report_data_availability"))
        self.assertContains(response, f'href="{reverse("report_index")}"')


class DataAvailabilityTranslationTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_clear_button_in_portuguese(self):
        with translation.override("pt-br"):
            url = reverse("report_data_availability")
        response = self.client.get(url)
        self.assertContains(response, ">Limpar</a>")
        self.assertNotContains(response, "Claro")
