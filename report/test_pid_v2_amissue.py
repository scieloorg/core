import csv
import io

from django.test import TestCase

from article.models import AMArticle, Article
from collection.models import Collection
from core import choices as core_choices
from core.users.models import User
from issue.models import AMIssue, Issue, IssueExporter
from journal.models import Journal, SciELOJournal
from report import pid_v2_amissue as report
from report.models import ReportCSV
from report.tasks import task_report_pid_v2_amissue

ISSN = "2636-2309"


class PidV2AMIssueReportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.collection = Collection.objects.create(
            creator=self.user, acron3="dom", is_active=True
        )
        self.journal = Journal.objects.create(creator=self.user, title="Journal")
        self.scielo_journal = SciELOJournal.objects.create(
            issn_scielo=ISSN,
            collection=self.collection,
            journal=self.journal,
            journal_acron="rscd",
        )
        self.issues = {
            key: Issue.objects.create(
                journal=self.journal,
                year=year,
                volume=volume,
                number=number,
                creator=self.user,
            )
            for key, year, volume, number in (
                ("A", "2024", "1", "1"),
                ("B", "2024", "1", "2"),
                ("C", "2024", "2", "1"),
                ("D", "2024", "2", "2"),
                ("E", "2023", "3", "1"),
            )
        }
        # somente os AMIssue do cenário (Issue.save pode gerar outros)
        AMIssue.objects.all().delete()
        for key, suffix in (("A", "0001"), ("B", "0002"), ("D", "0004")):
            self.add_am_issue(key, f"{ISSN}2024{suffix}")
        IssueExporter.objects.create(
            parent=self.issues["B"],
            collection=self.collection,
            pid=f"{ISSN}20240002",
            status=core_choices.EXPORTATION_STATUS_DONE,
            creator=self.user,
        )

    def add_am_issue(self, key, pid):
        AMIssue.objects.create(
            pid=pid,
            collection=self.collection,
            new_record=self.issues[key],
            creator=self.user,
        )

    def add_article(self, key, pid_v2, with_am_article=False):
        article = Article.objects.create(
            pid_v2=pid_v2,
            pid_v3=f"v3{pid_v2[-21:]}",
            issue=self.issues[key],
            journal=self.journal,
            creator=self.user,
        )
        if with_am_article:
            AMArticle.objects.create(
                pid=pid_v2,
                collection=self.collection,
                new_record=article,
                creator=self.user,
            )
        return article

    def categories(self):
        return {
            row["pid_v2"]: set(row["categories"].split("|"))
            for row in report.get_rows(self.scielo_journal)
        }

    def test_articles_with_am_article_are_not_listed(self):
        self.add_article("A", f"S{ISSN}2024000100001", with_am_article=True)

        self.assertEqual(self.categories(), {})

    def test_amissue_matches(self):
        self.add_article("A", f"S{ISSN}2024000100002")

        self.assertEqual(
            self.categories(), {f"S{ISSN}2024000100002": {report.AMISSUE_MATCHES}}
        )

    def test_amissue_differs_and_issue_exported_with_other_code(self):
        self.add_article("B", f"S{ISSN}2024000300001")

        self.assertEqual(
            self.categories(),
            {
                f"S{ISSN}2024000300001": {
                    report.AMISSUE_DIFFERS,
                    report.ISSUE_EXPORTED_WITH_OTHER_CODE,
                }
            },
        )

    def test_issue_without_amissue_using_pid_of_other_issue(self):
        self.add_article("A", f"S{ISSN}2024000100001", with_am_article=True)
        self.add_article("C", f"S{ISSN}2024000100009")

        self.assertEqual(
            self.categories(),
            {
                f"S{ISSN}2024000100009": {
                    report.ISSUE_WITHOUT_AMISSUE,
                    report.PREFIX_IN_OTHER_ISSUES,
                    report.PREFIX_IS_OTHER_ISSUE_PID,
                }
            },
        )

    def test_prefixes_differ_in_issue(self):
        self.add_article("D", f"S{ISSN}2024000400001")
        self.add_article("D", f"S{ISSN}2024000500002")

        self.assertEqual(
            self.categories(),
            {
                f"S{ISSN}2024000400001": {
                    report.AMISSUE_MATCHES,
                    report.PREFIXES_DIFFER_IN_ISSUE,
                },
                f"S{ISSN}2024000500002": {
                    report.AMISSUE_DIFFERS,
                    report.PREFIXES_DIFFER_IN_ISSUE,
                },
            },
        )

    def test_prefix_year_and_issn_differ(self):
        self.add_am_issue("E", f"{ISSN}20230001")
        self.add_article("E", "S1111-111120240001" "00001")

        self.assertEqual(
            self.categories(),
            {
                "S1111-11112024000100001": {
                    report.AMISSUE_DIFFERS,
                    report.PREFIX_YEAR_DIFFERS,
                    report.PREFIX_ISSN_DIFFERS,
                }
            },
        )

    def test_article_without_pid_v2(self):
        Article.objects.create(
            pid_v3="v3withoutpidv2",
            issue=self.issues["A"],
            journal=self.journal,
            creator=self.user,
        )

        rows = list(report.get_rows(self.scielo_journal))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["categories"], report.ARTICLE_WITHOUT_PID_V2)

    def test_task_saves_csv_by_journal(self):
        self.add_article("B", f"S{ISSN}2024000300001")

        result = task_report_pid_v2_amissue(
            collection_acron3="dom", user_id=self.user.id
        )

        self.assertEqual(result, {"rscd": 1})
        report_csv = ReportCSV.objects.get(
            journal=self.journal, title="pid_v2 x AMIssue dom"
        )
        with report_csv.file.open("rb") as fp:
            rows = list(csv.DictReader(io.StringIO(fp.read().decode("utf-8"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pid_v2"], f"S{ISSN}2024000300001")
        self.assertEqual(rows[0]["amissue_pids"], f"{ISSN}20240002")
        self.assertEqual(rows[0]["exported_issue_codes"], f"{ISSN}20240002")
