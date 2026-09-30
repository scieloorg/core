import csv
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase

from article.models import Article, ArticleCount, ArticleCountType
from collection.models import Collection
from core.models import Language
from journal.models import Journal, SciELOJournal, ThematicAreaJournal
from report.visual_element_totals import (
    filtered_article_ids,
    spreadsheet_rows,
    yearly_totals,
)
from thematic_areas.models import ThematicArea

User = get_user_model()


class VisualElementTotalsQueryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="report-user", password="x")
        self.collection_scl = Collection.objects.create(
            acron3="scl", creator=self.user
        )
        self.collection_arg = Collection.objects.create(
            acron3="arg", creator=self.user
        )
        self.area_health = ThematicArea.objects.create(
            level0="Health", creator=self.user
        )
        self.area_bio = ThematicArea.objects.create(
            level0="Biological", creator=self.user
        )
        self.journal = Journal.objects.create(
            title="Revista Teste",
            creator=self.user,
        )
        SciELOJournal.objects.create(
            journal=self.journal,
            collection=self.collection_scl,
            journal_acron="rtest",
            creator=self.user,
        )
        SciELOJournal.objects.create(
            journal=self.journal,
            collection=self.collection_arg,
            journal_acron="rtest",
            creator=self.user,
        )
        ThematicAreaJournal.objects.create(
            journal=self.journal,
            thematic_area=self.area_health,
            creator=self.user,
        )
        ThematicAreaJournal.objects.create(
            journal=self.journal,
            thematic_area=self.area_bio,
            creator=self.user,
        )
        self.lang_fr = Language.get_or_create(code2="fr", creator=self.user)
        self.lang_pt = Language.get_or_create(code2="pt", creator=self.user)
        self.lang_en = Language.get_or_create(code2="en", creator=self.user)
        self.lang_es = Language.get_or_create(code2="es", creator=self.user)
        self.fig_type, _ = ArticleCountType.objects.get_or_create(
            code=ArticleCountType.TYPE_FIG
        )
        self.table_type, _ = ArticleCountType.objects.get_or_create(
            code=ArticleCountType.TYPE_TABLE_WRAP
        )
        self.article = Article.objects.create(
            pid_v3="report-v3",
            journal=self.journal,
            pub_date_year="2024",
            creator=self.user,
        )
        for language, count in (
            (self.lang_fr, 1),
            (self.lang_pt, 2),
            (self.lang_en, 3),
            (self.lang_es, 4),
            (None, 5),
        ):
            ArticleCount.objects.create(
                article=self.article,
                count_type=self.fig_type,
                language=language,
                count=count,
            )
        ArticleCount.objects.create(
            article=self.article,
            count_type=self.table_type,
            language=self.lang_en,
            count=1,
        )
        self.article_without_year = Article.objects.create(
            pid_v3="report-no-year",
            journal=self.journal,
            creator=self.user,
        )
        ArticleCount.objects.create(
            article=self.article_without_year,
            count_type=self.fig_type,
            language=self.lang_en,
            count=99,
        )

    def test_includes_articles_without_pub_date_year(self):
        article_ids = list(filtered_article_ids())
        self.assertIn(self.article.id, article_ids)
        self.assertIn(self.article_without_year.id, article_ids)

    def test_collection_join_does_not_double_count(self):
        article_ids = list(filtered_article_ids(collection=self.collection_scl))
        self.assertIn(self.article.id, article_ids)
        self.assertEqual(len(article_ids), 2)
        rows = list(yearly_totals(article_ids))
        row_2024 = next(row for row in rows if row["article__pub_date_year"] == "2024")
        self.assertEqual(row_2024["fig"], 15)
        self.assertEqual(row_2024["table_wrap"], 1)

    def test_thematic_area_filter_counts_article_once(self):
        article_ids = list(filtered_article_ids(thematic_area=self.area_health))
        self.assertIn(self.article.id, article_ids)
        rows = list(yearly_totals(article_ids))
        row_2024 = next(row for row in rows if row["article__pub_date_year"] == "2024")
        self.assertEqual(row_2024["fig"], 15)

    def test_spreadsheet_columns_and_concatenated_thematic_areas(self):
        article_ids = list(filtered_article_ids())
        columns, rows = spreadsheet_rows(article_ids)
        self.assertEqual(columns[:4], ("collection", "thematic_area", "journal", "year"))
        fig_columns = [
            column
            for column in columns
            if column.startswith("fig-") or column == "fig_total"
        ]
        self.assertEqual(
            fig_columns,
            [
                "fig-en",
                "fig-es",
                "fig-fr",
                "fig-pt",
                "fig-nd",
                "fig_total",
            ],
        )
        self.assertIn("table-wrap-en", columns)
        self.assertIn("table-wrap-nd", columns)
        self.assertNotIn("table-wrap-pt", columns)
        self.assertIn("table-wrap_total", columns)
        self.assertNotIn("graphic-en", columns)
        self.assertEqual(len(rows), 2)
        row = next(item for item in rows if item["year"] == "2024")
        self.assertEqual(row["collection"], "arg; scl")
        self.assertEqual(row["journal"], "Revista Teste")
        self.assertEqual(row["year"], "2024")
        self.assertEqual(row["fig-fr"], 1)
        self.assertEqual(row["fig-pt"], 2)
        self.assertEqual(row["fig-en"], 3)
        self.assertEqual(row["fig-es"], 4)
        self.assertEqual(row["fig-nd"], 5)
        self.assertEqual(row["fig_total"], 15)
        self.assertEqual(row["table-wrap-en"], 1)
        self.assertEqual(row["table-wrap-nd"], 0)
        self.assertEqual(row["table-wrap_total"], 1)
        self.assertEqual(row["graphic_total"], 0)
        self.assertIn("Health", row["thematic_area"])
        self.assertIn("Biological", row["thematic_area"])

        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(columns)
        for row in rows:
            writer.writerow(
                [
                    "" if row.get(column) is None else row.get(column)
                    for column in columns
                ]
            )
        header = buffer.getvalue().splitlines()[0]
        self.assertEqual(header, ";".join(columns))

    def test_pid_matches_v2_or_v3(self):
        self.article.pid_v2 = "S0100-000020240001"
        self.article.save(update_fields=["pid_v2"])

        by_v3 = list(filtered_article_ids(pid="report-v3"))
        by_v2 = list(filtered_article_ids(pid="S0100-000020240001"))

        self.assertEqual(by_v3, [self.article.id])
        self.assertEqual(by_v2, [self.article.id])

    def test_missing_language_uses_nd_column(self):
        ArticleCount.objects.create(
            article=self.article,
            count_type=self.fig_type,
            language=None,
            count=4,
        )
        lang_nd = Language.get_or_create(code2="nd", creator=self.user)
        ArticleCount.objects.create(
            article=self.article,
            count_type=self.table_type,
            language=lang_nd,
            count=6,
        )
        columns, rows = spreadsheet_rows(list(filtered_article_ids()))
        row = next(item for item in rows if item["year"] == "2024")
        self.assertIn("fig-nd", columns)
        self.assertEqual(row["fig-nd"], 9)
        self.assertEqual(row["fig_total"], 19)
        self.assertEqual(row["table-wrap-nd"], 6)
        self.assertEqual(row["table-wrap_total"], 7)
        fig_columns = [
            column
            for column in columns
            if column.startswith("fig-") or column == "fig_total"
        ]
        self.assertEqual(fig_columns[-2], "fig-nd")
        self.assertEqual(fig_columns[-1], "fig_total")

    def test_filtered_collection_is_used_in_spreadsheet_column(self):
        article_ids = list(filtered_article_ids(collection=self.collection_arg))
        columns, rows = spreadsheet_rows(article_ids, collection=self.collection_arg)
        self.assertEqual(rows[0]["collection"], "arg")
        self.assertTrue(columns)
