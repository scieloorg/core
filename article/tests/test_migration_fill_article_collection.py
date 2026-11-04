from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from article.models import AMArticle, Article
from collection.models import Collection
from journal.models import Journal, SciELOJournal

User = get_user_model()

migration = import_module("article.migrations.0055_fill_article_collection")

PID_V2_SCL = "S0103-65642009000300003"
PID_V2_PSI = "S1678-51772009000300003"


class FillArticleCollectionMigrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fill_collection_user")
        self.scl = Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=self.user
        )
        self.psi = Collection.objects.create(acron3="psi", creator=self.user)
        self.rve = Collection.objects.create(acron3="rve", creator=self.user)

        # Psicologia USP: issn_scielo diferente em cada coleção
        self.pusp = self.make_journal(
            "pusp", ((self.scl, "0103-6564"), (self.psi, "1678-5177"))
        )
        # somente em scl
        self.single = self.make_journal("single", ((self.scl, "0000-0001"),))
        # mesmo issn_scielo em scl e psi
        self.csp = self.make_journal(
            "csp", ((self.psi, "0102-311X"), (self.scl, "0102-311X"))
        )
        # mesmo issn_scielo, nenhuma coleção principal
        self.rp = self.make_journal(
            "rp", ((self.psi, "0254-9247"), (self.rve, "0254-9247"))
        )

    def make_journal(self, title, collections):
        journal = Journal.objects.create(title=title, creator=self.user)
        for collection, issn_scielo in collections:
            SciELOJournal.objects.create(
                journal=journal,
                collection=collection,
                issn_scielo=issn_scielo,
                creator=self.user,
            )
        return journal

    def make_article(self, pid_v3, journal, pid_v2=None, collection=None):
        return Article.objects.create(
            pid_v3=pid_v3,
            pid_v2=pid_v2,
            journal=journal,
            collection=collection,
            creator=self.user,
        )

    def run_migration(self, batch_size=2):
        with patch.object(migration, "BATCH_SIZE", batch_size), patch("builtins.print"):
            migration.fill_article_collection(
                None, SimpleNamespace(connection=connection)
            )

    def assert_collection(self, article, expected):
        article.refresh_from_db()
        self.assertEqual(article.collection, expected, article.pid_v3)

    def test_legacy_article_with_same_pid_v2(self):
        article = self.make_article("v3-legacy", self.pusp, PID_V2_PSI)
        AMArticle.objects.create(
            pid=PID_V2_SCL, collection=self.scl, new_record=article, creator=self.user
        )
        AMArticle.objects.create(
            pid=PID_V2_PSI, collection=self.psi, new_record=article, creator=self.user
        )
        self.run_migration()
        self.assert_collection(article, self.psi)

    def test_issn_scielo_of_pid_v2(self):
        scl_item = self.make_article("v3-scl", self.pusp, PID_V2_SCL)
        psi_item = self.make_article("v3-psi", self.pusp, PID_V2_PSI)
        self.run_migration()
        self.assert_collection(scl_item, self.scl)
        self.assert_collection(psi_item, self.psi)

    def test_same_issn_scielo_uses_main_collection(self):
        article = self.make_article("v3-csp", self.csp, "S0102-311X2019000104001")
        self.run_migration()
        self.assert_collection(article, self.scl)

    def test_single_collection_journal(self):
        article = self.make_article("v3-single", self.single)
        self.run_migration()
        self.assert_collection(article, self.scl)

    def test_main_collection_of_the_journal(self):
        article = self.make_article("v3-main", self.pusp)
        self.run_migration()
        self.assert_collection(article, self.scl)

    def test_not_identified(self):
        article = self.make_article("v3-rp", self.rp, "S0254-92472019000104001")
        no_journal = self.make_article("v3-no-journal", None)
        self.run_migration()
        self.assert_collection(article, None)
        self.assert_collection(no_journal, None)

    def test_keeps_existing_collection(self):
        article = self.make_article("v3-kept", self.pusp, PID_V2_SCL, self.psi)
        self.run_migration()
        self.assert_collection(article, self.psi)

    def test_many_batches(self):
        articles = [
            self.make_article(f"v3-{i}", self.pusp, PID_V2_PSI) for i in range(7)
        ]
        self.run_migration(batch_size=3)
        for article in articles:
            self.assert_collection(article, self.psi)
