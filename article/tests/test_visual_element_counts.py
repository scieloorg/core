import tempfile

from lxml import etree
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from article.models import Article, ArticleCount, ArticleCountType
from article.sources.xmlsps import (
    count_visual_and_formula_items,
    create_or_update_article_counts,
)
from core.models import Language
from pid_provider.models import PidProviderXML, XMLVersion

User = get_user_model()

VISUAL_ELEMENTS_XML = """
<article xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="en" article-type="research-article">
  <front>
    <article-meta>
      <title-group><article-title>T</article-title></title-group>
    </article-meta>
  </front>
  <body>
    <fig id="f1"><graphic xlink:href="fig1.jpg"/></fig>
    <table-wrap id="t1"><graphic xlink:href="tab1.jpg"/></table-wrap>
    <p><graphic xlink:href="standalone.jpg"/></p>
    <p><inline-graphic xlink:href="inline.jpg"/></p>
    <disp-formula id="e1">
      <mml:math xmlns:mml="http://www.w3.org/1998/Math/MathML"><mml:mi>x</mml:mi></mml:math>
      <graphic xlink:href="eq1.jpg"/>
    </disp-formula>
    <p>
      <inline-formula>
        <mml:math xmlns:mml="http://www.w3.org/1998/Math/MathML"><mml:mi>y</mml:mi></mml:math>
      </inline-formula>
    </p>
  </body>
  <sub-article article-type="translation" xml:lang="pt" id="s1">
    <body>
      <fig id="f1-pt"><graphic xlink:href="fig1-pt.jpg"/></fig>
      <disp-formula id="e1-pt">
        <mml:math xmlns:mml="http://www.w3.org/1998/Math/MathML"><mml:mi>x</mml:mi></mml:math>
      </disp-formula>
    </body>
  </sub-article>
</article>
"""

XML_WITHOUT_LANG = """
<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="research-article">
  <body>
    <fig id="f1"><graphic xlink:href="fig1.jpg"/></fig>
  </body>
</article>
"""


def xmltree_from_string(xml):
    return etree.fromstring(xml.encode())


class CountVisualAndFormulaItemsTest(SimpleTestCase):
    def test_counts_by_parent_lang_and_excludes_graphic_inside_fig_and_table_wrap(self):
        errors = []
        counter = count_visual_and_formula_items(
            xmltree_from_string(VISUAL_ELEMENTS_XML)
        )

        self.assertEqual(counter[(ArticleCountType.TYPE_FIG, "en")], 1)
        self.assertEqual(counter[(ArticleCountType.TYPE_FIG, "pt")], 1)
        self.assertEqual(counter[(ArticleCountType.TYPE_TABLE_WRAP, "en")], 1)
        self.assertEqual(counter[(ArticleCountType.TYPE_DISP_FORMULA, "en")], 1)
        self.assertEqual(counter[(ArticleCountType.TYPE_DISP_FORMULA, "pt")], 1)
        self.assertEqual(counter[(ArticleCountType.TYPE_INLINE_FORMULA, "en")], 1)
        self.assertEqual(counter[(ArticleCountType.TYPE_GRAPHIC, "en")], 2)
        self.assertEqual(counter[(ArticleCountType.TYPE_INLINE_GRAPHIC, "en")], 1)
        self.assertNotIn((ArticleCountType.TYPE_GRAPHIC, "pt"), counter)
        self.assertEqual(errors, [])

    def test_missing_parent_lang_is_counted(self):
        errors = []
        counter = count_visual_and_formula_items(
            xmltree_from_string(XML_WITHOUT_LANG)
        )

        self.assertEqual(counter[(ArticleCountType.TYPE_FIG, None)], 1)
        self.assertEqual(errors, [])


class CreateOrUpdateArticleCountsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="counts_user", password="x")
        self.article = Article.objects.create(
            pid_v3="counts-v3", creator=self.user
        )

    def test_persists_totals_linked_to_article_by_type_and_language(self):
        errors = []
        create_or_update_article_counts(
            xmltree_from_string(VISUAL_ELEMENTS_XML),
            self.article,
            self.user,
            errors,
        )

        counts = {
            (item.count_type.code, item.language.code2): item.count
            for item in self.article.counts.select_related("count_type", "language")
        }
        self.assertEqual(counts[(ArticleCountType.TYPE_FIG, "en")], 1)
        self.assertEqual(counts[(ArticleCountType.TYPE_FIG, "pt")], 1)
        self.assertEqual(counts[(ArticleCountType.TYPE_GRAPHIC, "en")], 2)
        self.assertFalse(
            self.article.counts.filter(count=0).exists()
        )
        self.assertEqual(errors, [])

    def test_replaces_previous_counts(self):
        count_type, _ = ArticleCountType.objects.get_or_create(
            code=ArticleCountType.TYPE_FIG
        )
        language = Language.get_or_create(code2="es", creator=self.user)
        ArticleCount.objects.create(
            article=self.article,
            count_type=count_type,
            language=language,
            count=9,
        )

        create_or_update_article_counts(
            xmltree_from_string(VISUAL_ELEMENTS_XML),
            self.article,
            self.user,
            [],
        )

        self.assertFalse(
            self.article.counts.filter(
                count_type=count_type, language=language
            ).exists()
        )
        self.assertTrue(
            self.article.counts.filter(
                count_type__code=ArticleCountType.TYPE_FIG, language__code2="en"
            ).exists()
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class XMLVersionSaveFileUpdatesCountsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="xml_save_user", password="x")
        self.pp_xml = PidProviderXML.objects.create(
            creator=self.user,
            v3="COUNTSAVEFILEV3XXXXXXX",
            pkg_name="count-save-pkg",
        )
        self.article = Article.objects.create(
            pid_v3="count-save-article",
            pp_xml=self.pp_xml,
            creator=self.user,
        )

    def test_save_file_persists_counts_for_linked_article(self):
        version = XMLVersion.objects.create(
            pid_provider_xml=self.pp_xml,
            creator=self.user,
        )
        version.save_file(f"{self.pp_xml.v3}.xml", VISUAL_ELEMENTS_XML)

        self.assertEqual(
            self.article.counts.get(
                count_type__code=ArticleCountType.TYPE_FIG, language__code2="en"
            ).count,
            1,
        )
        self.assertEqual(
            self.article.counts.get(
                count_type__code=ArticleCountType.TYPE_FIG, language__code2="pt"
            ).count,
            1,
        )
        self.assertEqual(
            self.article.counts.get(
                count_type__code=ArticleCountType.TYPE_GRAPHIC, language__code2="en"
            ).count,
            2,
        )

    def test_save_file_without_article_does_not_raise(self):
        self.article.delete()
        version = XMLVersion.objects.create(
            pid_provider_xml=self.pp_xml,
            creator=self.user,
        )
        version.save_file(f"{self.pp_xml.v3}.xml", VISUAL_ELEMENTS_XML)
        self.assertFalse(ArticleCount.objects.filter(article__pp_xml=self.pp_xml).exists())
