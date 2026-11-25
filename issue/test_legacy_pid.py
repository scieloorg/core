import json

from django.test import TestCase
from django.urls import reverse

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


class IssueCreateFormLegacyPidTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="admin")
        self.client.force_login(self.user)
        self.journal = Journal.objects.create(creator=self.user, title="Test Journal")
        self.collections = {}
        for acron3, issn_scielo in (("scl", "1516-635X"), ("spa", "0034-8910")):
            self.collections[acron3] = Collection.objects.create(
                creator=self.user, acron3=acron3, is_active=True
            )
            SciELOJournal.objects.create(
                issn_scielo=issn_scielo,
                collection=self.collections[acron3],
                journal=self.journal,
                journal_acron="abdc",
            )
        self.other_collection = Collection.objects.create(
            creator=self.user, acron3="mex", is_active=True
        )

    def post(self, collections):
        data = {
            # AutocompletePanel envia o valor em JSON
            "journal": json.dumps({"pk": self.journal.pk}),
            "volume": "10",
            "number": "1",
            "year": "2024",
            "collections": [c.pk for c in collections],
        }
        for prefix in ("issue_title", "bibliographic_strip", "table_of_contents"):
            data[f"{prefix}-TOTAL_FORMS"] = "0"
            data[f"{prefix}-INITIAL_FORMS"] = "0"
        return self.client.post(reverse("wagtailsnippets_issue_issue:add"), data)

    def test_without_collections_suggests_journal_collections(self):
        response = self.post([])

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Issue.objects.exists())
        form = response.context["form"]
        self.assertIn("collections", form.errors)
        self.assertEqual(
            set(form["collections"].value()),
            {str(c.pk) for c in self.collections.values()},
        )

    def test_creates_am_issue_only_for_confirmed_collections(self):
        response = self.post([self.collections["spa"]])

        self.assertEqual(response.status_code, 302)
        issue = Issue.objects.get(journal=self.journal)
        self.assertEqual(
            dict(issue.legacy_issue.values_list("collection__acron3", "pid")),
            {"spa": "0034-891020240001"},
        )

    def test_creates_am_issue_for_each_confirmed_collection(self):
        response = self.post(self.collections.values())

        self.assertEqual(response.status_code, 302)
        issue = Issue.objects.get(journal=self.journal)
        self.assertEqual(
            dict(issue.legacy_issue.values_list("collection__acron3", "pid")),
            {"scl": "1516-635X20240001", "spa": "0034-891020240001"},
        )

    def test_rejects_collection_without_journal(self):
        response = self.post([self.collections["scl"], self.other_collection])

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Issue.objects.exists())
        self.assertIn("collections", response.context["form"].errors)

    def test_edit_form_has_no_collections(self):
        issue = Issue.create(
            user=self.user,
            journal=self.journal,
            number="1",
            volume="10",
            season=None,
            year="2024",
            month=None,
            supplement=None,
        )

        response = self.client.get(
            reverse("wagtailsnippets_issue_issue:edit", args=[issue.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("collections", response.context["form"].fields)
