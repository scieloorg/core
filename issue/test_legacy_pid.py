from django.test import TestCase

from collection.models import Collection
from core.users.models import User
from issue.models import AMIssue, Issue
from journal.models import Journal, SciELOJournal


class IssueLegacyPidCollisionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="teste", password="teste")
        self.collection = Collection.objects.create(
            creator=self.user, acron3="scl", is_active=True
        )
        self.journal = Journal.objects.create(creator=self.user, title="Test Journal")
        SciELOJournal.objects.create(
            issn_scielo="1516-635X",
            collection=self.collection,
            journal=self.journal,
            journal_acron="abdc",
        )

    def create_issue(self, volume, number):
        return Issue.create(
            user=self.user,
            journal=self.journal,
            number=number,
            volume=volume,
            season=None,
            year="2024",
            month=None,
            supplement=None,
        )

    def test_issues_with_same_suffix_get_distinct_pids(self):
        # v10n1 e v11n1 no mesmo ano têm o mesmo sufixo (0001)
        issue_1 = self.create_issue("10", "1")
        issue_2 = self.create_issue("11", "1")
        self.assertEqual(issue_1.issue_pid_suffix, issue_2.issue_pid_suffix)

        issue_1.create_legacy_keys(self.user)
        issue_2.create_legacy_keys(self.user)

        am_issue_1 = AMIssue.objects.get(new_record=issue_1)
        am_issue_2 = AMIssue.objects.get(new_record=issue_2)
        self.assertEqual(am_issue_1.pid, "1516-635X20240001")
        self.assertEqual(am_issue_2.pid, "1516-635X20240002")

    def test_pid_harvested_from_am_without_issue_is_not_reused(self):
        AMIssue.objects.create(
            pid="1516-635X20240001",
            collection=self.collection,
            creator=self.user,
        )
        issue = self.create_issue("10", "1")

        issue.create_legacy_keys(self.user)

        self.assertEqual(
            AMIssue.objects.get(new_record=issue).pid, "1516-635X20240002"
        )
        self.assertIsNone(
            AMIssue.objects.get(pid="1516-635X20240001").new_record
        )
