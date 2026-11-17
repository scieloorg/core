"""
Testes de carga de dados do XML (SPS) para Article.

Os testes são caixa-preta: dado um XML, verificam como Article (e os modelos
ligados a ele) fica preenchido depois de `load_article`.

- A entrada é o próprio XML, gravado como versão de um PidProviderXML,
  exatamente como acontece em produção. Não há mocks.
- Os valores esperados foram escritos a partir da leitura do XML. A camada
  que extrai os dados do XML é ignorada pelos testes: qualquer mudança nela
  (refatoração, troca de versão, bug) que altere o que é gravado em Article
  faz algum teste falhar.

Os testes marcados com `expectedFailure` documentam divergências conhecidas
entre o que o XML contém e o que é gravado hoje. Quando a divergência for
corrigida eles passam a acusar "unexpected success" e o decorator deve ser
removido.
"""

import tempfile
import unittest

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from article import choices
from article.models import (
    Article,
    ArticleAffiliation,
    ArticleCountType,
    ContribCollab,
    DocumentAbstract,
)
from article.sources.xmlsps import load_article
from collection.models import Collection
from core.models import Language
from doi.models import DOI
from issue.models import Issue, TableOfContents
from journal.models import Journal, OfficialJournal
from pid_provider import choices as pp_choices
from pid_provider.models import PidProviderXML, XMLVersion
from vocabulary.models import Vocabulary

User = get_user_model()


XML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "https://jats.nlm.nih.gov/publishing/1.1/JATS-journalpublishing1.dtd">
<article xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" article-type="research-article" dtd-version="1.1" specific-use="sps-1.9" xml:lang="pt">
  <front>
    <journal-meta>
      <journal-id journal-id-type="publisher-id">tjr</journal-id>
      <journal-title-group>
        <journal-title>Test Journal of Regression</journal-title>
        <abbrev-journal-title abbrev-type="publisher">Test J. Regr.</abbrev-journal-title>
      </journal-title-group>
      <issn pub-type="ppub">1234-5678</issn>
      <issn pub-type="epub">8765-4321</issn>
      <publisher>
        <publisher-name>Test Publisher</publisher-name>
      </publisher>
    </journal-meta>
    <article-meta>
      <article-id pub-id-type="publisher-id" specific-use="scielo-v3">TstV3pidRegressionXmlAA</article-id>
      <article-id pub-id-type="publisher-id" specific-use="scielo-v2">S1234-56782024000200005</article-id>
      <article-id pub-id-type="other">00005</article-id>
      <article-id pub-id-type="doi">10.1590/1234-5678.2024.0005</article-id>
      <article-categories>
        <subj-group subj-group-type="heading">
          <subject>Artigos Originais</subject>
        </subj-group>
      </article-categories>
      <title-group>
        <article-title>Título em <bold>português</bold></article-title>
        <trans-title-group xml:lang="es">
          <trans-title>Título en español</trans-title>
        </trans-title-group>
      </title-group>
      <contrib-group>
        <contrib contrib-type="author">
          <contrib-id contrib-id-type="orcid">0000-0002-1825-0097</contrib-id>
          <name>
            <surname>Silva</surname>
            <given-names>Maria</given-names>
            <suffix>Jr</suffix>
          </name>
          <xref ref-type="aff" rid="aff1">1</xref>
          <xref ref-type="aff" rid="aff2">2</xref>
        </contrib>
        <contrib contrib-type="author">
          <name>
            <surname>Souza</surname>
            <given-names>João</given-names>
          </name>
          <xref ref-type="aff" rid="aff1">1</xref>
          <xref ref-type="corresp" rid="c1">*</xref>
        </contrib>
        <contrib contrib-type="author">
          <name>
            <surname>Lima</surname>
            <given-names>Ana</given-names>
          </name>
          <email>ana.lima@example.org</email>
        </contrib>
        <contrib contrib-type="author">
          <collab>Grupo de Pesquisa em Regressão</collab>
          <xref ref-type="aff" rid="aff2">2</xref>
        </contrib>
      </contrib-group>
      <aff id="aff1">
        <label>1</label>
        <institution content-type="original">Universidade de São Paulo, Faculdade de Medicina, Departamento de Clínica. São Paulo, SP, Brasil</institution>
        <institution content-type="orgname">Universidade de São Paulo</institution>
        <institution content-type="orgdiv1">Faculdade de Medicina</institution>
        <institution content-type="orgdiv2">Departamento de Clínica</institution>
        <addr-line>
          <named-content content-type="city">São Paulo</named-content>
          <named-content content-type="state">SP</named-content>
        </addr-line>
        <country country="BR">Brasil</country>
      </aff>
      <aff id="aff2">
        <label>2</label>
        <institution content-type="original">Universidade Federal do Rio de Janeiro, Instituto de Biologia. Rio de Janeiro, RJ, Brasil</institution>
        <institution content-type="orgname">Universidade Federal do Rio de Janeiro</institution>
        <institution content-type="orgdiv1">Instituto de Biologia</institution>
        <addr-line>
          <named-content content-type="city">Rio de Janeiro</named-content>
          <named-content content-type="state">RJ</named-content>
        </addr-line>
        <country country="BR">Brasil</country>
      </aff>
      <author-notes>
        <corresp id="c1"><label>*</label>Correspondência: <email>joao.souza@usp.br</email></corresp>
      </author-notes>
      <pub-date publication-format="electronic" date-type="pub">
        <day>15</day>
        <month>03</month>
        <year>2024</year>
      </pub-date>
      <pub-date publication-format="electronic" date-type="collection">
        <month>06</month>
        <year>2024</year>
      </pub-date>
      <volume>10</volume>
      <issue>2</issue>
      <fpage>100</fpage>
      <lpage>110</lpage>
      <history>
        <date date-type="preprint">
          <day>01</day>
          <month>12</month>
          <year>2023</year>
        </date>
        <date date-type="received">
          <day>01</day>
          <month>01</month>
          <year>2024</year>
        </date>
        <date date-type="accepted">
          <day>01</day>
          <month>02</month>
          <year>2024</year>
        </date>
      </history>
      <permissions>
        <license license-type="open-access" xlink:href="https://creativecommons.org/licenses/by/4.0/" xml:lang="pt">
          <license-p>Este é um artigo publicado em acesso aberto sob uma licença Creative Commons</license-p>
        </license>
      </permissions>
      <related-article related-article-type="corrected-article" id="ra1" xlink:href="10.1590/1234-5678.2023.0001" ext-link-type="doi"/>
      <abstract>
        <title>Resumo</title>
        <p>Resumo em <italic>português</italic>.</p>
      </abstract>
      <trans-abstract xml:lang="es">
        <title>Resumen</title>
        <p>Resumen en español.</p>
      </trans-abstract>
      <kwd-group xml:lang="pt">
        <title>Palavras-chave</title>
        <kwd>saúde</kwd>
        <kwd><bold>regressão</bold></kwd>
      </kwd-group>
      <kwd-group xml:lang="es">
        <title>Palabras clave</title>
        <kwd>salud</kwd>
      </kwd-group>
      <funding-group>
        <award-group>
          <funding-source>CNPq</funding-source>
          <funding-source>FAPESP</funding-source>
          <award-id>123456/2024-0</award-id>
        </award-group>
      </funding-group>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Introdução</title>
      <p>Texto com <inline-graphic xlink:href="1234-5678-tjr-10-2-100-i01.jpg"/> e <inline-formula><mml:math><mml:mi>y</mml:mi></mml:math></inline-formula>.</p>
      <fig id="f1">
        <label>Figura 1</label>
        <caption><title>Figura</title></caption>
        <graphic xlink:href="1234-5678-tjr-10-2-100-gf01.jpg"/>
      </fig>
      <table-wrap id="t1">
        <label>Tabela 1</label>
        <caption><title>Tabela</title></caption>
        <graphic xlink:href="1234-5678-tjr-10-2-100-gt01.jpg"/>
      </table-wrap>
      <disp-formula id="e1">
        <mml:math><mml:mi>x</mml:mi></mml:math>
      </disp-formula>
      <graphic xlink:href="1234-5678-tjr-10-2-100-g01.jpg"/>
    </sec>
  </body>
  <back>
    <sec sec-type="data-availability" specific-use="data-available">
      <title>Disponibilidade de dados</title>
      <p>Os dados estão disponíveis no repositório institucional.</p>
    </sec>
  </back>
  <sub-article article-type="translation" id="s1" xml:lang="en">
    <front-stub>
      <article-id pub-id-type="doi">10.1590/1234-5678.2024.0005.en</article-id>
      <article-categories>
        <subj-group subj-group-type="heading">
          <subject>Original Articles</subject>
        </subj-group>
      </article-categories>
      <title-group>
        <article-title>Title in <bold>English</bold></article-title>
      </title-group>
      <abstract>
        <title>Abstract</title>
        <p>Abstract in <bold>English</bold>.</p>
      </abstract>
      <kwd-group xml:lang="en">
        <title>Keywords</title>
        <kwd>health</kwd>
        <kwd>regression</kwd>
      </kwd-group>
    </front-stub>
    <body>
      <sec>
        <title>Introduction</title>
        <p>Text.</p>
        <fig id="f1-en">
          <label>Figure 1</label>
          <caption><title>Figure</title></caption>
          <graphic xlink:href="1234-5678-tjr-10-2-100-gf01-en.jpg"/>
        </fig>
      </sec>
    </body>
    <back>
      <sec sec-type="data-availability" specific-use="data-available">
        <title>Data availability</title>
        <p>The data are available in the institutional repository.</p>
      </sec>
    </back>
  </sub-article>
</article>
"""

# ---------------------------------------------------------------------------
# Valores esperados, lidos diretamente do XML acima
# ---------------------------------------------------------------------------
JOURNAL_TITLE = "Test Journal of Regression"  # journal-title
ISSN_PRINT = "1234-5678"  # issn[@pub-type="ppub"]
ISSN_ELECTRONIC = "8765-4321"  # issn[@pub-type="epub"]

EXPECTED_PID_V3 = "TstV3pidRegressionXmlAA"  # article-id[@specific-use="scielo-v3"]
EXPECTED_PID_V2 = "S1234-56782024000200005"  # article-id[@specific-use="scielo-v2"]

EXPECTED_ARTICLE_TYPE = "research-article"  # article/@article-type

# idiomas do documento: article/@xml:lang e
# sub-article[@article-type="translation"]/@xml:lang; idiomas que aparecem
# apenas em metadados (trans-title, trans-abstract, kwd-group: es) não contam
EXPECTED_LANGUAGES = {"pt", "en"}

# volume / issue / pub-date[@date-type="pub"]/year
EXPECTED_ISSUE = {"volume": "10", "number": "2", "year": "2024"}

# pub-date[@date-type="pub"] (tem precedência sobre date-type="collection")
EXPECTED_PUB_DATE = {"day": "15", "month": "03", "year": "2024"}

EXPECTED_PAGES = {"first_page": "100", "last_page": "110", "elocation_id": None}

# license/@xlink:href = https://creativecommons.org/licenses/by/4.0/
EXPECTED_LICENSE = ("by", "4.0")

# history: preprint 2023-12-01, received 2024-01-01, accepted 2024-02-01;
# pub-date pub 2024-03-15. Todas as datas são completas, então nenhum
# intervalo é estimado.
EXPECTED_PEER_REVIEW = {
    "preprint_dateiso": "2023-12-01",
    "received_dateiso": "2024-01-01",
    "accepted_dateiso": "2024-02-01",
    "days_preprint_to_received": 31,  # dez/2023: 31 dias
    "days_received_to_accepted": 31,  # jan/2024: 31 dias
    "days_accepted_to_published": 43,  # fev/2024 (29 dias) + 14
    "days_preprint_to_published": 105,  # 31 + 31 + 43
    "days_receive_to_published": 74,  # 31 + 43
    "days_preprint_to_received_estimated": False,
    "days_received_to_accepted_estimated": False,
    "days_accepted_to_published_estimated": False,
    "days_preprint_to_published_estimated": False,
    "days_receive_to_published_estimated": False,
}

# sec[@sec-type="data-availability"]/@specific-use e o texto dos <p>, por idioma
EXPECTED_DATA_AVAILABILITY_STATUS = "data-available"
EXPECTED_DATA_AVAILABILITY_STATEMENTS = {
    ("pt", "Os dados estão disponíveis no repositório institucional."),
    ("en", "The data are available in the institutional repository."),
}

# subj-group[@subj-group-type="heading"]/subject (article e sub-article)
EXPECTED_SECTIONS = {
    ("pt", "Artigos Originais"),
    ("en", "Original Articles"),
}

# (idioma, texto puro, texto com <bold> convertido para <b>)
EXPECTED_TITLES = {
    ("pt", "Título em português", "Título em <b>português</b>"),
    ("es", "Título en español", "Título en español"),
    ("en", "Title in English", "Title in <b>English</b>"),
}

# Conteúdo do resumo: os <p>, sem o <title> ("Resumo", "Abstract"...)
EXPECTED_ABSTRACTS_PLAIN = {
    ("pt", "Resumo em português."),
    ("es", "Resumen en español."),
    ("en", "Abstract in English."),
}
# idem, com <italic> -> <i> e <bold> -> <b>
EXPECTED_ABSTRACTS_RICH = {
    ("pt", "Resumo em <i>português</i>."),
    ("es", "Resumen en español."),
    ("en", "Abstract in <b>English</b>."),
}

# kwd: (idioma, texto puro, texto com <bold> convertido para <b>)
EXPECTED_KEYWORDS = {
    ("pt", "saúde", "saúde"),
    ("pt", "regressão", "<b>regressão</b>"),
    ("es", "salud", "salud"),
    ("en", "health", "health"),
    ("en", "regression", "regression"),
}

# Um ContribPerson por combinação autor x afiliação; autor sem afiliação gera
# um registro com affiliation=None; contrib com <collab> não é pessoa.
# (given_names, last_name, suffix, orcid, orgname da afiliação)
EXPECTED_CONTRIB_PERSONS = {
    ("Maria", "Silva", "Jr", "0000-0002-1825-0097", "Universidade de São Paulo"),
    (
        "Maria",
        "Silva",
        "Jr",
        "0000-0002-1825-0097",
        "Universidade Federal do Rio de Janeiro",
    ),
    ("João", "Souza", None, None, "Universidade de São Paulo"),
    ("Ana", "Lima", None, None, None),
}

# (last_name, email)
EXPECTED_CONTRIB_EMAILS = {
    ("Silva", None),
    ("Souza", "joao.souza@usp.br"),  # xref corresp -> corresp[@id="c1"]/email
    ("Lima", "ana.lima@example.org"),  # contrib/email
}

# aff: (orgname, orgdiv1, orgdiv2, país, código do país, estado, cidade)
EXPECTED_AFFILIATIONS = {
    (
        "Universidade de São Paulo",
        "Faculdade de Medicina",
        "Departamento de Clínica",
        "Brasil",
        "BR",
        "SP",
        "São Paulo",
    ),
    (
        "Universidade Federal do Rio de Janeiro",
        "Instituto de Biologia",
        None,
        "Brasil",
        "BR",
        "RJ",
        "Rio de Janeiro",
    ),
}

# (collab, orgname da afiliação)
EXPECTED_COLLABS = {
    ("Grupo de Pesquisa em Regressão", "Universidade Federal do Rio de Janeiro"),
}

# funding-source x award-id do mesmo award-group
EXPECTED_FUNDINGS = {
    ("CNPq", "123456/2024-0"),
    ("FAPESP", "123456/2024-0"),
}

# article-id[@pub-id-type="doi"] do article e do sub-article
EXPECTED_DOIS = {
    ("pt", "10.1590/1234-5678.2024.0005"),
    ("en", "10.1590/1234-5678.2024.0005.en"),
}

# related-article: (xlink:href, ext-link-type, related-article-type)
EXPECTED_RELATED_ARTICLES = {
    ("10.1590/1234-5678.2023.0001", "doi", "corrected-article"),
}

# elementos visuais e fórmulas por idioma; graphic dentro de fig/table-wrap
# conta como fig/table-wrap, não como graphic
EXPECTED_COUNTS = {
    (ArticleCountType.TYPE_FIG, "pt"): 1,
    (ArticleCountType.TYPE_FIG, "en"): 1,
    (ArticleCountType.TYPE_TABLE_WRAP, "pt"): 1,
    (ArticleCountType.TYPE_DISP_FORMULA, "pt"): 1,
    (ArticleCountType.TYPE_INLINE_FORMULA, "pt"): 1,
    (ArticleCountType.TYPE_GRAPHIC, "pt"): 1,
    (ArticleCountType.TYPE_INLINE_GRAPHIC, "pt"): 1,
}


def replace_once(text, old, new):
    """Substitui exatamente uma ocorrência; falha se o trecho não existir."""
    assert text.count(old) == 1, f"trecho não encontrado (ou repetido): {old!r}"
    return text.replace(old, new)


def remove_history_date(xml, date_type, day, month, year):
    return replace_once(
        xml,
        f'        <date date-type="{date_type}">\n'
        f"          <day>{day}</day>\n"
        f"          <month>{month}</month>\n"
        f"          <year>{year}</year>\n"
        "        </date>\n",
        "",
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class XMLToArticleTestCase(TestCase):
    """
    Base: cria no banco o que precisa existir antes da carga (journal, issue
    com sumário, idiomas e vocabulário padrão) e oferece `load(xml)`, que
    registra o XML como versão de um PidProviderXML e executa load_article.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="xmlsps-loader", password="x")
        cls.collection = Collection.objects.create(
            acron3="tst", domain="www.test.org", is_active=True, creator=cls.user
        )
        for code2 in ("pt", "en", "es"):
            Language.get_or_create(code2=code2, creator=cls.user)
        Vocabulary.create_or_update(cls.user, acronym="nd", name="Not defined")

        cls.official = OfficialJournal.objects.create(
            title=JOURNAL_TITLE,
            issn_print=ISSN_PRINT,
            issn_electronic=ISSN_ELECTRONIC,
            creator=cls.user,
        )
        cls.journal = Journal.objects.create(
            title=JOURNAL_TITLE, official=cls.official, creator=cls.user
        )
        cls.issue = cls.create_issue(**EXPECTED_ISSUE)

    @classmethod
    def create_issue(cls, volume, number, year, supplement=None):
        issue = Issue.create(
            user=cls.user,
            journal=cls.journal,
            number=number,
            volume=volume,
            season=None,
            year=year,
            month=None,
            supplement=supplement,
        )
        for lang, title in sorted(EXPECTED_SECTIONS):
            TableOfContents.create_or_update(
                cls.user, issue, cls.collection, lang, title, "AO"
            )
        return issue

    @classmethod
    def create_pp_xml(cls, xml):
        # pkg_name aqui só define o diretório do arquivo; propositalmente
        # diferente de EXPECTED_SPS_PKG_NAME, que deve vir do XML
        pp_xml = PidProviderXML.objects.create(
            creator=cls.user, v3=EXPECTED_PID_V3, pkg_name="pp-registered-name"
        )
        version = XMLVersion.objects.create(pid_provider_xml=pp_xml, creator=cls.user)
        version.save_file(f"{EXPECTED_PID_V3}.xml", xml)
        pp_xml.current_version = version
        pp_xml.save()
        return pp_xml

    @classmethod
    def load(cls, xml):
        return load_article(cls.user, pp_xml=cls.create_pp_xml(xml))


class LoadArticleFromXMLTest(XMLToArticleTestCase):
    """Carga do XML completo: cada teste verifica um grupo de campos."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.article_id = cls.load(XML).pk

    def setUp(self):
        self.article = Article.objects.get(pk=self.article_id)

    def test_load_finishes_without_errors(self):
        self.assertNotIn("errors", self.article.errors or {})
        self.assertTrue(self.article.valid)
        self.assertEqual(self.article.data_status, choices.DATA_STATUS_COMPLETED)
        self.assertEqual(
            self.article.pp_xml.proc_status, pp_choices.PPXML_STATUS_DONE
        )

    def test_pids(self):
        self.assertEqual(self.article.pid_v3, EXPECTED_PID_V3)
        self.assertEqual(self.article.pid_v2, EXPECTED_PID_V2)

    def test_sps_pkg_name(self):
        # O formato do nome do pacote depende de uma regra de composição
        # (não é um dado nativo do XML), então não é verificado aqui; só se
        # exige que exista e que não seja outro identificador.
        self.assertTrue(self.article.sps_pkg_name)
        self.assertNotIn(
            self.article.sps_pkg_name, (EXPECTED_PID_V3, EXPECTED_PID_V2)
        )

    def test_article_type(self):
        self.assertEqual(self.article.article_type, EXPECTED_ARTICLE_TYPE)

    def test_journal(self):
        self.assertEqual(self.article.journal, self.journal)

    def test_issue(self):
        self.assertEqual(self.article.issue, self.issue)

    def test_pub_date(self):
        self.assertEqual(
            {
                "day": self.article.pub_date_day,
                "month": self.article.pub_date_month,
                "year": self.article.pub_date_year,
            },
            EXPECTED_PUB_DATE,
        )

    def test_pages(self):
        self.assertEqual(
            {name: getattr(self.article, name) for name in EXPECTED_PAGES},
            EXPECTED_PAGES,
        )

    def test_license(self):
        self.assertEqual(
            (self.article.license.license_type, self.article.license.version),
            EXPECTED_LICENSE,
        )

    def test_peer_review_dates_and_intervals(self):
        names = [n for n in EXPECTED_PEER_REVIEW if not n.endswith("_estimated")]
        self.assertEqual(
            {name: getattr(self.article, name) for name in names},
            {name: EXPECTED_PEER_REVIEW[name] for name in names},
        )

    @unittest.expectedFailure
    def test_peer_review_intervals_are_not_estimated(self):
        # Divergência conhecida: com todas as datas completas os campos
        # *_estimated ficam None em vez de False.
        names = [n for n in EXPECTED_PEER_REVIEW if n.endswith("_estimated")]
        self.assertEqual(
            {name: getattr(self.article, name) for name in names},
            {name: EXPECTED_PEER_REVIEW[name] for name in names},
        )

    def test_peer_review_stats_has_the_dates(self):
        values = set(map(str, self.article.peer_review_stats.values()))
        self.assertTrue(
            {"2023-12-01", "2024-01-01", "2024-02-01", "2024-03-15"} <= values
        )

    def test_data_availability(self):
        self.assertEqual(
            self.article.data_availability_status, EXPECTED_DATA_AVAILABILITY_STATUS
        )
        self.assertIsNone(self.article.invalid_data_availability_status)
        got = {
            (item.language.code2, item.text)
            for item in self.article.data_availability_statements.all()
        }
        self.assertEqual(got, EXPECTED_DATA_AVAILABILITY_STATEMENTS)

    def test_main_language(self):
        self.assertIn("pt", {lang.code2 for lang in self.article.languages.all()})

    @unittest.expectedFailure
    def test_languages(self):
        # Divergência conhecida: só o idioma principal é gravado; o idioma da
        # tradução (sub-article) não entra em Article.languages.
        self.assertEqual(
            {lang.code2 for lang in self.article.languages.all()},
            EXPECTED_LANGUAGES,
        )

    def test_sections(self):
        got = {
            (item.journal_toc.language.code2, item.journal_toc.text)
            for item in self.article.sections.all()
        }
        self.assertEqual(got, EXPECTED_SECTIONS)

    def test_titles(self):
        got = {
            (item.language.code2, item.plain_text, item.rich_text)
            for item in self.article.titles.all()
        }
        self.assertEqual(got, EXPECTED_TITLES)

    def test_abstracts_languages(self):
        self.assertEqual(
            {item.language.code2 for item in self.article.abstracts.all()},
            {lang for lang, _ in EXPECTED_ABSTRACTS_PLAIN},
        )

    @unittest.expectedFailure
    def test_abstracts_plain_text(self):
        # Divergência conhecida: o texto gravado começa com o <title> do
        # resumo ("Resumo Resumo em português.").
        got = {
            (item.language.code2, item.plain_text)
            for item in self.article.abstracts.all()
        }
        self.assertEqual(got, EXPECTED_ABSTRACTS_PLAIN)

    def test_abstracts_rich_text_is_filled_on_first_load(self):
        got = {
            item.language.code2: item.rich_text or ""
            for item in self.article.abstracts.all()
        }
        for lang, rich_text in EXPECTED_ABSTRACTS_RICH:
            with self.subTest(lang=lang):
                self.assertIn(rich_text, got.get(lang, ""))

    @unittest.expectedFailure
    def test_abstracts_rich_text(self):
        # Divergência conhecida: o texto gravado começa com o <title> do
        # resumo (ver test_abstracts_plain_text).
        got = {
            (item.language.code2, item.rich_text)
            for item in self.article.abstracts.all()
        }
        self.assertEqual(got, EXPECTED_ABSTRACTS_RICH)

    def test_keywords(self):
        got = {
            (item.language.code2, item.text, item.html_text)
            for item in self.article.keywords.all()
        }
        self.assertEqual(got, EXPECTED_KEYWORDS)

    def get_contrib_persons(self):
        return [
            (
                item.given_names,
                item.last_name,
                item.suffix,
                item.orcid,
                item.affiliation and item.affiliation.raw_institution_name,
            )
            for item in self.article.contrib_persons.select_related("affiliation")
        ]

    def test_contrib_persons_with_single_or_no_affiliation(self):
        got = self.get_contrib_persons()
        self.assertIn(("João", "Souza", None, None, "Universidade de São Paulo"), got)
        self.assertIn(("Ana", "Lima", None, None, None), got)

    def test_contrib_person_orcid_and_suffix(self):
        silva = self.article.contrib_persons.filter(last_name="Silva")
        self.assertTrue(silva.exists())
        for item in silva:
            self.assertEqual(
                (item.given_names, item.suffix, item.orcid),
                ("Maria", "Jr", "0000-0002-1825-0097"),
            )

    def test_contrib_person_with_multiple_affiliations(self):
        # um ContribPerson por afiliação do autor
        got = {
            item[4]
            for item in self.get_contrib_persons()
            if item[1] == "Silva"
        }
        self.assertEqual(
            got,
            {"Universidade de São Paulo", "Universidade Federal do Rio de Janeiro"},
        )

    def test_collab_is_not_contrib_person(self):
        self.assertFalse(
            self.article.contrib_persons.filter(
                given_names__isnull=True, last_name__isnull=True
            ).exists()
        )

    def test_contrib_persons(self):
        got = self.get_contrib_persons()
        self.assertEqual(set(got), EXPECTED_CONTRIB_PERSONS)
        self.assertEqual(len(got), len(EXPECTED_CONTRIB_PERSONS))

    @unittest.expectedFailure
    def test_contrib_persons_email(self):
        # Divergência conhecida: o email (de contrib/email ou do corresp
        # referenciado pelo autor) não é gravado em ContribPerson.email.
        got = {
            (item.last_name, item.email)
            for item in self.article.contrib_persons.filter(last_name__isnull=False)
        }
        self.assertEqual(got, EXPECTED_CONTRIB_EMAILS)

    def test_affiliations(self):
        got = {
            (
                item.raw_institution_name,
                item.raw_level_1,
                item.raw_level_2,
                item.raw_country_name,
                item.raw_country_code,
                item.raw_state_name,
                item.raw_city_name,
            )
            for item in ArticleAffiliation.objects.filter(article=self.article)
        }
        self.assertEqual(got, EXPECTED_AFFILIATIONS)

    def test_contrib_collabs(self):
        got = {
            (item.collab, item.affiliation and item.affiliation.raw_institution_name)
            for item in ContribCollab.objects.filter(article=self.article)
        }
        self.assertEqual(got, EXPECTED_COLLABS)

    def test_fundings(self):
        got = {
            (item.funding_source.institution_name, item.award_id)
            for item in self.article.fundings.all()
        }
        self.assertEqual(got, EXPECTED_FUNDINGS)

    def test_doi(self):
        got = {(item.language.code2, item.value) for item in self.article.doi.all()}
        self.assertEqual(got, EXPECTED_DOIS)

    def test_related_articles(self):
        got = {
            (item.href, item.ext_link_type, item.related_type)
            for item in self.article.related_articles.all()
        }
        self.assertEqual(got, EXPECTED_RELATED_ARTICLES)

    def test_counts(self):
        got = {
            (item.count_type.code, item.language and item.language.code2): item.count
            for item in self.article.counts.select_related("count_type", "language")
        }
        self.assertEqual(got, EXPECTED_COUNTS)


class ReloadArticleFromXMLTest(XMLToArticleTestCase):
    """Recarregar o mesmo XML atualiza o mesmo Article sem duplicar dados."""

    def test_reload_keeps_same_article_and_does_not_duplicate(self):
        pp_xml = self.create_pp_xml(XML)
        first = load_article(self.user, pp_xml=pp_xml)

        def snapshot(article):
            return {
                "contrib_persons": article.contrib_persons.count(),
                "contrib_collabs": ContribCollab.objects.filter(article=article).count(),
                "affiliations": ArticleAffiliation.objects.filter(
                    article=article
                ).count(),
                "titles": article.titles.count(),
                "abstracts": DocumentAbstract.objects.filter(article=article).count(),
                "keywords": article.keywords.count(),
                "doi": article.doi.count(),
                "fundings": article.fundings.count(),
                "related_articles": article.related_articles.count(),
                "data_availability_statements": (
                    article.data_availability_statements.count()
                ),
                "sections": article.sections.count(),
                "languages": article.languages.count(),
                "counts": article.counts.count(),
            }

        before = snapshot(first)
        second = load_article(self.user, pp_xml=pp_xml)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Article.objects.filter(pid_v3=EXPECTED_PID_V3).count(), 1)
        self.assertNotIn("errors", second.errors or {})
        self.assertEqual(snapshot(second), before)


class LoadArticleXMLVariationsTest(XMLToArticleTestCase):
    """Variações do XML e o efeito correspondente em Article."""

    def test_elocation_id_instead_of_pages(self):
        xml = replace_once(
            XML,
            "<fpage>100</fpage>\n      <lpage>110</lpage>",
            "<elocation-id>e2024005</elocation-id>",
        )
        article = self.load(xml)
        self.assertEqual(
            (article.first_page, article.last_page, article.elocation_id),
            (None, None, "e2024005"),
        )

    def test_pub_date_falls_back_to_collection_date(self):
        xml = replace_once(
            XML,
            '      <pub-date publication-format="electronic" date-type="pub">\n'
            "        <day>15</day>\n"
            "        <month>03</month>\n"
            "        <year>2024</year>\n"
            "      </pub-date>\n",
            "",
        )
        article = self.load(xml)
        self.assertEqual(
            (article.pub_date_day, article.pub_date_month, article.pub_date_year),
            (None, "06", "2024"),
        )

    def test_without_preprint_date(self):
        xml = remove_history_date(XML, "preprint", "01", "12", "2023")
        article = self.load(xml)
        self.assertIsNone(article.preprint_dateiso)
        self.assertIsNone(article.days_preprint_to_received)
        self.assertIsNone(article.days_preprint_to_published)
        self.assertEqual(article.received_dateiso, "2024-01-01")
        self.assertEqual(article.days_received_to_accepted, 31)

    def test_without_history(self):
        xml = remove_history_date(XML, "preprint", "01", "12", "2023")
        xml = remove_history_date(xml, "received", "01", "01", "2024")
        xml = remove_history_date(xml, "accepted", "01", "02", "2024")
        article = self.load(xml)
        for name in (
            "preprint_dateiso",
            "received_dateiso",
            "accepted_dateiso",
            "days_preprint_to_received",
            "days_received_to_accepted",
            "days_accepted_to_published",
            "days_preprint_to_published",
            "days_receive_to_published",
        ):
            with self.subTest(name=name):
                self.assertIsNone(getattr(article, name))

    def test_incomplete_received_date_makes_interval_estimated(self):
        xml = replace_once(
            XML,
            '<date date-type="received">\n'
            "          <day>01</day>\n",
            '<date date-type="received">\n',
        )
        article = self.load(xml)
        self.assertIsNotNone(article.days_received_to_accepted)
        self.assertTrue(article.days_received_to_accepted_estimated)
        self.assertTrue(article.days_receive_to_published_estimated)

    def test_data_availability_absent(self):
        xml = XML.replace(
            'sec-type="data-availability" specific-use="data-available"',
            'sec-type="other"',
        )
        article = self.load(xml)
        self.assertEqual(
            article.data_availability_status,
            choices.DATA_AVAILABILITY_STATUS_ABSENT,
        )
        self.assertIsNone(article.invalid_data_availability_status)
        self.assertFalse(article.data_availability_statements.exists())

    def test_data_availability_invalid_value_is_preserved(self):
        xml = XML.replace(
            'specific-use="data-available"', 'specific-use="not-a-valid-status"'
        )
        article = self.load(xml)
        self.assertEqual(
            article.data_availability_status,
            choices.DATA_AVAILABILITY_STATUS_INVALID,
        )
        self.assertEqual(
            article.invalid_data_availability_status, "not-a-valid-status"
        )

    def test_data_availability_other_valid_value(self):
        xml = XML.replace(
            'specific-use="data-available"',
            'specific-use="data-available-upon-request"',
        )
        article = self.load(xml)
        self.assertEqual(
            article.data_availability_status,
            choices.DATA_AVAILABILITY_STATUS_UPON_REQUEST,
        )
        self.assertIsNone(article.invalid_data_availability_status)

    def test_license_with_version_and_jurisdiction(self):
        xml = replace_once(
            XML,
            "https://creativecommons.org/licenses/by/4.0/",
            "https://creativecommons.org/licenses/by-nc/3.0/br/",
        )
        article = self.load(xml)
        self.assertEqual(
            (article.license.license_type, article.license.version),
            ("by-nc", "3.0"),
        )

    def test_article_type_and_main_language(self):
        xml = replace_once(
            XML,
            'article-type="research-article" dtd-version="1.1" '
            'specific-use="sps-1.9" xml:lang="pt"',
            'article-type="review-article" dtd-version="1.1" '
            'specific-use="sps-1.9" xml:lang="es"',
        )
        article = self.load(xml)
        self.assertEqual(article.article_type, "review-article")
        self.assertIn("es", {lang.code2 for lang in article.languages.all()})
        self.assertNotIn("pt", {lang.code2 for lang in article.languages.all()})

    def test_fundings_from_several_award_groups(self):
        xml = replace_once(
            XML,
            "</award-group>\n",
            "</award-group>\n"
            "        <award-group>\n"
            "          <funding-source>CAPES</funding-source>\n"
            "          <award-id>001</award-id>\n"
            "          <award-id>002</award-id>\n"
            "        </award-group>\n",
        )
        article = self.load(xml)
        got = {
            (item.funding_source.institution_name, item.award_id)
            for item in article.fundings.all()
        }
        self.assertEqual(
            got,
            EXPECTED_FUNDINGS | {("CAPES", "001"), ("CAPES", "002")},
        )

    def test_funding_source_without_award_id_is_not_a_funding(self):
        xml = replace_once(XML, "<award-id>123456/2024-0</award-id>", "")
        article = self.load(xml)
        self.assertFalse(article.fundings.exists())

    def test_related_article_points_to_existing_article_with_that_doi(self):
        corrected = Article.objects.create(pid_v3="CorrectedArticlePidV3XX", creator=self.user)
        corrected.doi.add(
            DOI.objects.create(value="10.1590/1234-5678.2023.0001", creator=self.user)
        )
        article = self.load(XML)
        related = article.related_articles.get()
        self.assertEqual(related.related_article, corrected)

    def test_journal_found_by_issn_when_title_differs(self):
        xml = XML.replace(JOURNAL_TITLE, "Another Title")
        article = self.load(xml)
        self.assertEqual(article.journal, self.journal)

    def test_issue_with_supplement(self):
        issue = self.create_issue(volume="10", number="2", year="2024", supplement="1")
        xml = replace_once(XML, "<issue>2</issue>", "<issue>2 suppl 1</issue>")
        article = self.load(xml)
        self.assertEqual(article.issue, issue)

    def test_journal_not_found_raises(self):
        xml = XML.replace(JOURNAL_TITLE, "Unknown Journal")
        xml = replace_once(xml, ISSN_PRINT + "</issn>", "0000-0000</issn>")
        xml = replace_once(xml, ISSN_ELECTRONIC + "</issn>", "0000-0001</issn>")
        with self.assertRaisesMessage(ValueError, "Not found journal"):
            self.load(xml)

    def test_issue_not_found_raises(self):
        xml = replace_once(XML, "<volume>10</volume>", "<volume>99</volume>")
        with self.assertRaisesMessage(ValueError, "Not found issue"):
            self.load(xml)

    def test_without_pid_v2_raises_and_keeps_article_not_valid(self):
        xml = replace_once(
            XML,
            '<article-id pub-id-type="publisher-id" specific-use="scielo-v2">'
            f"{EXPECTED_PID_V2}</article-id>",
            "",
        )
        with self.assertRaisesMessage(ValueError, "Article has no PID v2"):
            self.load(xml)
        article = Article.objects.get(pid_v3=EXPECTED_PID_V3)
        self.assertFalse(article.valid)
        self.assertIn("errors", article.errors)
