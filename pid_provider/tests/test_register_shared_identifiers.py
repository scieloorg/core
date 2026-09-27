"""
Testes de integração de PidProviderXML.register quando artigos diferentes
compartilham um identificador que deveria ser exclusivo.

Reproduz o problema relatado na execução de
`task_load_records_from_counter_dict` para o periódico BJM da coleção scl:
`PidProvider.provide_pid_for_xml_uri` falhou com
QueryDocumentMultipleObjectsReturnedError porque no PidProviderXML há mais de
um registro com o mesmo:

- aop_pid: S1517-83822015005040098 está registrado para
  vTQdGGLzjLB9t9bkv7KRkhw (S1517-83822015000300759) e para
  6tVtNpdVbNjLPFLFptwhDSH
- pkg_name: o nome de pacote de n4YgC9hXSXqDGJSzrRBBqJM
  (S1517-83822013000200047) está registrado também para
  9fWvbZ7pXXKWr4HTCtqjjjq

Nos dois casos, os demais identificadores (pid v3 e pid v2) e o conteúdo do
XML são suficientes para identificar um único registro, então o registro
deve ser encontrado e atualizado, sem erro.
"""

from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre

from collection.models import Collection
from journal.models import Journal, OfficialJournal, SciELOJournal
from pid_provider.models import PidProviderXML

User = get_user_model()

ISSN_PRINT = "1517-8382"
ISSN_ELECTRONIC = "1678-4405"

# mesmo aop_pid registrado para artigos diferentes
AOP_PID = "S1517-83822015005040098"
AOP_ARTICLE = dict(
    v3="vTQdGGLzjLB9t9bkv7KRkhw",
    v2="S1517-83822015000300759",
    aop_pid=AOP_PID,
    doi="10.1590/S1517-838246320140359",
    year="2015",
    volume="46",
    issue="3",
    fpage="759",
    lpage="766",
    title="Antimicrobial activity of essential oils against foodborne bacteria",
    surnames=("Oliveira", "Pereira"),
    body=(
        "Essential oils were extracted by hydrodistillation and tested "
        "against Staphylococcus aureus and Escherichia coli isolated from "
        "food samples."
    ),
)
OTHER_AOP_ARTICLE = dict(
    v3="6tVtNpdVbNjLPFLFptwhDSH",
    v2="S1517-83822015000300767",
    aop_pid=AOP_PID,
    doi="10.1590/S1517-838246320140412",
    year="2015",
    volume="46",
    issue="3",
    fpage="767",
    lpage="775",
    title="Biofilm formation by Pseudomonas aeruginosa on stainless steel",
    surnames=("Santos", "Almeida"),
    body=(
        "Biofilm formation was evaluated on stainless steel coupons exposed "
        "to clinical isolates of Pseudomonas aeruginosa under static "
        "conditions."
    ),
)

# mesmo pkg_name registrado para artigos diferentes
PKG_NAME_ARTICLE = dict(
    v3="n4YgC9hXSXqDGJSzrRBBqJM",
    v2="S1517-83822013000200047",
    aop_pid=None,
    doi="10.1590/S1517-83822013000200047",
    year="2013",
    volume="44",
    issue="2",
    fpage="347",
    lpage="352",
    title="Detection of Salmonella spp. in poultry carcasses by real-time PCR",
    surnames=("Costa", "Ferreira"),
    body=(
        "Poultry carcasses were collected from slaughterhouses and analysed "
        "by real-time PCR targeting the invA gene of Salmonella spp."
    ),
)
OTHER_PKG_NAME_ARTICLE = dict(
    v3="9fWvbZ7pXXKWr4HTCtqjjjq",
    v2="S1517-83822013000200048",
    aop_pid=None,
    doi="10.1590/S1517-83822013000200048",
    year="2013",
    volume="44",
    issue="2",
    fpage="353",
    lpage="360",
    title="Diversity of endophytic fungi isolated from Amazonian medicinal plants",
    surnames=("Lima", "Rodrigues"),
    body=(
        "Endophytic fungi were isolated from leaves of medicinal plants "
        "collected in the Amazon region and identified by ITS sequencing."
    ),
)

XML_TEMPLATE = """<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "https://jats.nlm.nih.gov/publishing/1.1/JATS-journalpublishing1.dtd">
<article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" article-type="research-article" dtd-version="1.1" specific-use="sps-1.9" xml:lang="en">
  <front>
    <journal-meta>
      <journal-id journal-id-type="publisher-id">bjm</journal-id>
      <journal-title-group>
        <journal-title>Brazilian Journal of Microbiology</journal-title>
      </journal-title-group>
      <issn pub-type="ppub">1517-8382</issn>
      <issn pub-type="epub">1678-4405</issn>
    </journal-meta>
    <article-meta>
      <article-id specific-use="scielo-v3" pub-id-type="publisher-id">{v3}</article-id>
      <article-id specific-use="scielo-v2" pub-id-type="publisher-id">{v2}</article-id>
      {aop_pid_node}
      <article-id pub-id-type="doi">{doi}</article-id>
      <article-categories>
        <subj-group subj-group-type="heading">
          <subject>Research Paper</subject>
        </subj-group>
      </article-categories>
      <title-group>
        <article-title>{title}</article-title>
      </title-group>
      <contrib-group>
        {contribs}
      </contrib-group>
      <pub-date date-type="pub" publication-format="electronic">
        <day>21</day>
        <month>07</month>
        <year>{year}</year>
      </pub-date>
      <pub-date date-type="collection" publication-format="electronic">
        <year>{year}</year>
      </pub-date>
      <volume>{volume}</volume>
      <issue>{issue}</issue>
      <fpage>{fpage}</fpage>
      <lpage>{lpage}</lpage>
    </article-meta>
  </front>
  <body>
    <p>{body}</p>
  </body>
</article>
"""

CONTRIB_TEMPLATE = """<contrib contrib-type="author">
          <name>
            <surname>{surname}</surname>
            <given-names>A.</given-names>
          </name>
        </contrib>"""


def make_xml_with_pre(article):
    aop_pid = article.get("aop_pid")
    aop_pid_node = (
        f'<article-id specific-use="previous-pid" pub-id-type="publisher-id">{aop_pid}</article-id>'
        if aop_pid
        else ""
    )
    contribs = "\n        ".join(
        CONTRIB_TEMPLATE.format(surname=surname) for surname in article["surnames"]
    )
    xml_content = XML_TEMPLATE.format(
        aop_pid_node=aop_pid_node,
        contribs=contribs,
        **{k: v for k, v in article.items() if k not in ("aop_pid", "surnames")},
    )
    xml_with_pre = list(XMLWithPre.create(xml_content=xml_content))[0]
    xml_with_pre.collection = "scl"
    return xml_with_pre


class RegisterWithIdentifierSharedByOtherArticleMixin:
    # artigo que está sendo carregado e o outro artigo que, no
    # PidProviderXML, tem o mesmo identificador
    article = None
    other_article = None

    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.override_settings = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.override_settings.enable()
        self.addCleanup(self.override_settings.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.user = User.objects.create_user(username="shared-identifiers")
        scl = Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=self.user
        )
        official_journal = OfficialJournal.objects.create(
            title="Brazilian Journal of Microbiology",
            issn_print=ISSN_PRINT,
            issn_electronic=ISSN_ELECTRONIC,
            creator=self.user,
        )
        journal = Journal.objects.create(
            official=official_journal, creator=self.user
        )
        SciELOJournal.objects.create(
            journal=journal,
            collection=scl,
            journal_acron="bjm",
            issn_scielo=ISSN_PRINT,
            creator=self.user,
        )

        for article in (self.article, self.other_article):
            self.assert_no_error(
                self.register(make_xml_with_pre(article), f"scl_{article['v3']}")
            )
        self.share_identifier()
        self.assertEqual(PidProviderXML.objects.count(), 2)

    def share_identifier(self):
        """
        Reproduz o estado do PidProviderXML: o outro artigo com o mesmo
        identificador do artigo
        """
        raise NotImplementedError

    def register(self, xml_with_pre, filename):
        # como em provide_pid_for_xml_uri (ver Detail do Unexpected Event)
        return PidProviderXML.register(
            xml_with_pre, filename, self.user, origin_date="2021-08-31"
        )

    def assert_no_error(self, response):
        self.assertIsNone(
            response.get("error_type"),
            f"{response.get('error_msg')} {response.get('select_record_response')}",
        )

    def test_register_identifies_the_article(self):
        response = self.register(
            make_xml_with_pre(self.article), f"scl_{self.article['v3']}"
        )

        self.assert_no_error(response)
        self.assertNotEqual(response.get("event_status"), "multiple")
        self.assertEqual(response["v3"], self.article["v3"])
        self.assertEqual(response["v2"], self.article["v2"])
        # não cria novo registro nem altera o outro artigo
        self.assertEqual(PidProviderXML.objects.count(), 2)
        other = PidProviderXML.objects.get(v3=self.other_article["v3"])
        self.assertEqual(other.v2, self.other_article["v2"])

    def test_register_identifies_the_other_article(self):
        response = self.register(
            make_xml_with_pre(self.other_article),
            f"scl_{self.other_article['v3']}",
        )

        self.assert_no_error(response)
        self.assertEqual(response["v3"], self.other_article["v3"])
        self.assertEqual(response["v2"], self.other_article["v2"])
        self.assertEqual(PidProviderXML.objects.count(), 2)

    def test_is_registered_identifies_the_article(self):
        response = PidProviderXML.is_registered(make_xml_with_pre(self.article))

        self.assert_no_error(response)
        self.assertTrue(response["registered"])
        self.assertEqual(response["v3"], self.article["v3"])
        self.assertEqual(response["v2"], self.article["v2"])


class RegisterWithAopPidSharedByOtherArticleTest(
    RegisterWithIdentifierSharedByOtherArticleMixin, TestCase
):
    """
    vTQdGGLzjLB9t9bkv7KRkhw e 6tVtNpdVbNjLPFLFptwhDSH com o mesmo aop_pid
    """

    article = AOP_ARTICLE
    other_article = OTHER_AOP_ARTICLE

    def share_identifier(self):
        PidProviderXML.objects.filter(
            v3__in=(self.article["v3"], self.other_article["v3"])
        ).update(aop_pid=AOP_PID)
        self.assertEqual(PidProviderXML.objects.filter(aop_pid=AOP_PID).count(), 2)


class RegisterWithPkgNameSharedByOtherArticleTest(
    RegisterWithIdentifierSharedByOtherArticleMixin, TestCase
):
    """
    n4YgC9hXSXqDGJSzrRBBqJM e 9fWvbZ7pXXKWr4HTCtqjjjq com o mesmo pkg_name
    """

    article = PKG_NAME_ARTICLE
    other_article = OTHER_PKG_NAME_ARTICLE

    def share_identifier(self):
        pkg_name = PidProviderXML.objects.get(v3=self.article["v3"]).pkg_name
        self.assertTrue(pkg_name)
        PidProviderXML.objects.filter(v3=self.other_article["v3"]).update(
            pkg_name=pkg_name
        )
        self.assertEqual(PidProviderXML.objects.filter(pkg_name=pkg_name).count(), 2)
