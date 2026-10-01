"""
Testes de integração de PidProviderXML.register com 2 XML que representam
o mesmo artigo em coleções diferentes.

Ex.: Psicologia USP
- scl: acron=pusp, pid=0103-6564, artigo S0103-65642009000300003
- psi: acron=psicousp, pid=1678-5177, artigo S1678-51772009000300003

Os XML têm o mesmo conteúdo, diferem no pid v2 (e no acrônimo do
periódico), informam a coleção de origem (custom-meta, como em
ArticleProc) e não têm pid v3 (como os XML gerados a partir do site clássico).

- somente o XML da coleção principal é a versão atual do documento
  (PidProviderXML.current_version)
- o pid v2 principal (PidProviderXML.v2) é somente o da coleção principal;
  a resposta do registro traz o pid v2 do XML recebido
- o pid v2 e a versão do XML de cada coleção ficam em CollectionPidV2
"""

from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre

from collection.models import ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY, Collection
from journal.models import Journal, OfficialJournal, SciELOJournal
from pid_provider.models import (
    CollectionPidV2,
    OtherPid,
    PidProviderXML,
    XMLVersion,
)

User = get_user_model()

SCL_V2 = "S0103-65642009000300003"
PSI_V2 = "S1678-51772009000300003"
ISSN_PRINT = "0103-6564"
ISSN_ELECTRONIC = "1678-5177"


def pid_v2_data(pid_v2, journal_acron, collection_acron, is_main):
    # CollectionPidV2.data
    return {
        "pid_v2": pid_v2,
        "journal_acron": journal_acron,
        "collection_acron": collection_acron,
        "is_main": is_main,
    }


SCL_DATA = pid_v2_data(SCL_V2, "pusp", "scl", True)
PSI_DATA = pid_v2_data(PSI_V2, "psicousp", "psi", False)

XML_TEMPLATE = """<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "https://jats.nlm.nih.gov/publishing/1.1/JATS-journalpublishing1.dtd">
<article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" article-type="research-article" dtd-version="1.1" specific-use="sps-1.9" xml:lang="pt">
  <front>
    <journal-meta>
      <journal-id journal-id-type="publisher-id">{journal_acron}</journal-id>
      <journal-title-group>
        <journal-title>Psicologia USP</journal-title>
      </journal-title-group>
      <issn pub-type="ppub">0103-6564</issn>
      <issn pub-type="epub">1678-5177</issn>
    </journal-meta>
    <article-meta>
      <article-id specific-use="scielo-v2" pub-id-type="publisher-id">{pid_v2}</article-id>
      <article-id pub-id-type="other">00003</article-id>
      <article-categories>
        <subj-group subj-group-type="heading">
          <subject>Artigos</subject>
        </subj-group>
      </article-categories>
      <title-group>
        <article-title>A constituição do sujeito e o laço social</article-title>
      </title-group>
      <contrib-group>
        <contrib contrib-type="author">
          <name>
            <surname>Silva</surname>
            <given-names>Maria</given-names>
          </name>
        </contrib>
        <contrib contrib-type="author">
          <name>
            <surname>Souza</surname>
            <given-names>João</given-names>
          </name>
        </contrib>
      </contrib-group>
      <pub-date date-type="pub" publication-format="electronic">
        <day>01</day>
        <month>09</month>
        <year>2009</year>
      </pub-date>
      <pub-date date-type="collection" publication-format="electronic">
        <year>2009</year>
      </pub-date>
      <volume>20</volume>
      <issue>3</issue>
      <fpage>333</fpage>
      <lpage>350</lpage>
    </article-meta>
  </front>
  <body>
    <p>Este artigo discute a constituição do sujeito a partir do laço social, considerando as contribuições da psicanálise para a compreensão das relações entre o indivíduo e a cultura contemporânea.</p>
    <p>Discute-se, ainda, o lugar do outro na formação da subjetividade e as consequências clínicas dessa perspectiva.</p>
  </body>
</article>
"""


TITLE = "A constituição do sujeito e o laço social"
UPDATED_TITLE = "A constituição do sujeito e do laço social"

# Errata: documento próprio (article-type="correction"), com pid v2 próprio,
# sem resumo e sem autores, contendo somente os trechos "onde se lê X,
# leia-se Y" e o related-article que aponta para o artigo corrigido
SCL_ERRATUM_V2 = "S0103-65642009000300010"
PSI_ERRATUM_V2 = "S1678-51772009000300010"

ERRATUM_TEMPLATE = """<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.1 20151215//EN" "https://jats.nlm.nih.gov/publishing/1.1/JATS-journalpublishing1.dtd">
<article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" article-type="correction" dtd-version="1.1" specific-use="sps-1.9" xml:lang="pt">
  <front>
    <journal-meta>
      <journal-id journal-id-type="publisher-id">{journal_acron}</journal-id>
      <journal-title-group>
        <journal-title>Psicologia USP</journal-title>
      </journal-title-group>
      <issn pub-type="ppub">0103-6564</issn>
      <issn pub-type="epub">1678-5177</issn>
    </journal-meta>
    <article-meta>
      <article-id specific-use="scielo-v2" pub-id-type="publisher-id">{pid_v2}</article-id>
      <article-id pub-id-type="other">00010</article-id>
      <article-categories>
        <subj-group subj-group-type="heading">
          <subject>Errata</subject>
        </subj-group>
      </article-categories>
      <title-group>
        <article-title>Errata</article-title>
      </title-group>
      <pub-date date-type="pub" publication-format="electronic">
        <day>15</day>
        <month>10</month>
        <year>2009</year>
      </pub-date>
      <pub-date date-type="collection" publication-format="electronic">
        <year>2009</year>
      </pub-date>
      <volume>20</volume>
      <issue>3</issue>
      <fpage>351</fpage>
      <lpage>351</lpage>
      <related-article ext-link-type="doi" id="ra1" related-article-type="corrected-article" xlink:href="10.1590/S0103-65642009000300003"/>
    </article-meta>
  </front>
  <body>
    <p>No artigo "A constituição do sujeito e o laço social", publicado no v. 20, n. 3, p. 333-350, 2009:</p>
    <p>Onde se lê: "A constituição do sujeito e o laço social"</p>
    <p>Leia-se: "A constituição do sujeito e do laço social"</p>
  </body>
</article>
"""


def make_xml_with_pre(pid_v2, journal_acron, collection=None, content=None):
    xml_content = content or XML_TEMPLATE.format(
        pid_v2=pid_v2, journal_acron=journal_acron
    )
    xml_with_pre = list(XMLWithPre.create(xml_content=xml_content))[0]
    if collection:
        # coleção de origem do XML (ver ArticleProc)
        xml_with_pre.collection = collection
    return xml_with_pre


def scl_xml():
    return make_xml_with_pre(SCL_V2, "pusp", "scl")


def psi_xml():
    return make_xml_with_pre(PSI_V2, "psicousp", "psi")


def updated_xml(pid_v2, journal_acron, collection):
    # nova versão do XML do mesmo artigo (mesmo pid v2), com o título corrigido
    content = XML_TEMPLATE.format(
        pid_v2=pid_v2, journal_acron=journal_acron
    ).replace(TITLE, UPDATED_TITLE)
    return make_xml_with_pre(pid_v2, journal_acron, collection, content)


def erratum_xml(pid_v2, journal_acron, collection):
    content = ERRATUM_TEMPLATE.format(
        pid_v2=pid_v2, journal_acron=journal_acron
    )
    return make_xml_with_pre(pid_v2, journal_acron, collection, content)


class RegisterSameArticleInDifferentCollectionsTestBase(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.override_settings = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.override_settings.enable()
        self.addCleanup(self.override_settings.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.user = User.objects.create_user(username="multicol-register")
        self.scl = Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=self.user
        )
        self.psi = Collection.objects.create(
            acron3="psi", network_classification=["thematic"], creator=self.user
        )
        official_journal = OfficialJournal.objects.create(
            title="Psicologia USP",
            issn_print=ISSN_PRINT,
            issn_electronic=ISSN_ELECTRONIC,
            creator=self.user,
        )
        journal = Journal.objects.create(
            official=official_journal, creator=self.user
        )
        SciELOJournal.objects.create(
            journal=journal,
            collection=self.scl,
            journal_acron="pusp",
            issn_scielo=ISSN_PRINT,
            creator=self.user,
        )
        SciELOJournal.objects.create(
            journal=journal,
            collection=self.psi,
            journal_acron="psicousp",
            issn_scielo=ISSN_ELECTRONIC,
            creator=self.user,
        )

    def register(self, xml_with_pre, filename):
        response = PidProviderXML.register(
            xml_with_pre, filename, self.user, origin_date="2026-01-01"
        )
        self.assertIsNone(
            response.get("error_type"),
            f"{response.get('error_msg')} {response.get('traceback')}",
        )
        return response

    def assert_same_article_registered_once(self, first, second):
        self.assertEqual(PidProviderXML.objects.count(), 1)
        registered = PidProviderXML.objects.get()
        self.assertEqual(first["v3"], registered.v3)
        self.assertEqual(second["v3"], registered.v3)
        self.assertEqual(first["ppx_id"], second["ppx_id"])
        return registered

    def assert_pids_v2_by_collection(self, registered, main="scl"):
        self.assertCountEqual(
            registered.collection_pids_v2_data,
            [
                pid_v2_data(SCL_V2, "pusp", "scl", main == "scl"),
                pid_v2_data(PSI_V2, "psicousp", "psi", main == "psi"),
            ],
        )
        self.assertEqual(
            {
                (item.collection.acron3, item.journal_acron, item.journal_pid, item.pid_v2)
                for item in CollectionPidV2.objects.filter(
                    pid_provider_xml=registered
                )
            },
            {
                ("scl", "pusp", ISSN_PRINT, SCL_V2),
                ("psi", "psicousp", ISSN_ELECTRONIC, PSI_V2),
            },
        )

    def collection_current_version(self, registered, collection):
        return CollectionPidV2.objects.get(
            pid_provider_xml=registered, collection=collection
        ).current_version

    def assert_current_version_is_from(self, registered, collection):
        registered.refresh_from_db()
        self.assertEqual(
            registered.current_version,
            self.collection_current_version(registered, collection),
        )

    def assert_no_pid_v2_change(self, registered):
        # pid v2 de outra coleção não é mudança de pid v2
        self.assertFalse(
            OtherPid.objects.filter(
                pid_provider_xml=registered, pid_type="pid_v2"
            ).exists()
        )


class RegisterMainCollectionFirstTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """scl (coleção principal) é registrado antes de psi (temática)"""

    def test_second_xml_is_identified_as_the_same_article(self):
        first = self.register(scl_xml(), "scl")
        second = self.register(psi_xml(), "psi")

        self.assertEqual(first["event_status"], "created")
        self.assertEqual(second["event_status"], "updated")
        registered = self.assert_same_article_registered_once(first, second)
        # xml de psi recebe o mesmo pid v3
        self.assertEqual(second["xml_changed"], {"pid_v3": registered.v3})

    def test_main_v2_is_kept_and_v2_by_collection_is_registered(self):
        self.register(scl_xml(), "scl")
        second = self.register(psi_xml(), "psi")

        registered = PidProviderXML.objects.get()
        self.assertEqual(registered.v2, SCL_V2)
        # a resposta traz o pid v2 do XML recebido
        self.assertEqual(second["v2"], PSI_V2)
        self.assertCountEqual(second["collection_pids_v2"], [SCL_DATA, PSI_DATA])
        self.assert_pids_v2_by_collection(registered)
        self.assert_no_pid_v2_change(registered)

    def test_registering_alternately_keeps_main_v2(self):
        responses = [
            self.register(scl_xml(), "scl"),
            self.register(psi_xml(), "psi"),
            self.register(scl_xml(), "scl"),
            self.register(psi_xml(), "psi"),
        ]

        registered = PidProviderXML.objects.get()
        self.assertEqual({item["v3"] for item in responses}, {registered.v3})
        self.assertEqual(registered.v2, SCL_V2)
        self.assertEqual(CollectionPidV2.objects.count(), 2)
        self.assert_no_pid_v2_change(registered)

    def test_is_registered_identifies_xml_of_both_collections(self):
        created = self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        for xml_with_pre in (scl_xml(), psi_xml()):
            with self.subTest(v2=xml_with_pre.v2):
                response = PidProviderXML.is_registered(xml_with_pre)
                self.assertTrue(response["registered"])
                self.assertEqual(response["v3"], created["v3"])
                # a resposta traz o pid v2 do XML de entrada
                self.assertEqual(response["v2"], xml_with_pre.v2)

    def test_pids_v2_of_both_collections_are_not_free(self):
        self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        self.assertTrue(PidProviderXML._is_registered_pid(v2=SCL_V2))
        self.assertTrue(PidProviderXML._is_registered_pid(v2=PSI_V2))


class RegisterThematicCollectionFirstTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """psi (temática) é registrado antes de scl (coleção principal)"""

    def test_second_xml_is_identified_as_the_same_article(self):
        first = self.register(psi_xml(), "psi")
        second = self.register(scl_xml(), "scl")

        self.assertEqual(first["event_status"], "created")
        self.assertEqual(second["event_status"], "updated")
        self.assert_same_article_registered_once(first, second)

    def test_main_collection_v2_becomes_the_main_v2(self):
        first = self.register(psi_xml(), "psi")
        self.assertEqual(first["v2"], PSI_V2)

        second = self.register(scl_xml(), "scl")

        registered = PidProviderXML.objects.get()
        self.assertEqual(registered.v2, SCL_V2)
        self.assertEqual(second["v2"], SCL_V2)
        self.assert_pids_v2_by_collection(registered)
        self.assert_no_pid_v2_change(registered)

    def test_thematic_collection_does_not_replace_main_v2_afterwards(self):
        self.register(psi_xml(), "psi")
        self.register(scl_xml(), "scl")
        self.register(updated_xml(PSI_V2, "psicousp", "psi"), "psi")

        registered = PidProviderXML.objects.get()
        self.assertEqual(registered.v2, SCL_V2)
        self.assert_pids_v2_by_collection(registered)


class RegisterWithoutMainCollectionTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """nenhuma das coleções é classificada como scielonetwork"""

    def setUp(self):
        super().setUp()
        Collection.objects.update(network_classification=None)

    def test_main_v2_is_not_registered(self):
        first = self.register(psi_xml(), "psi")
        second = self.register(scl_xml(), "scl")

        # a resposta traz o pid v2 do XML recebido
        self.assertEqual(first["v2"], PSI_V2)
        self.assertEqual(second["v2"], SCL_V2)
        registered = PidProviderXML.objects.get()
        # sem coleção principal, v2 não é completado
        self.assertIsNone(registered.v2)
        for xml_with_pre in (psi_xml(), scl_xml()):
            with self.subTest(v2=xml_with_pre.v2):
                response = PidProviderXML.is_registered(xml_with_pre)
                self.assertTrue(response["registered"])
                self.assertEqual(response["v2"], xml_with_pre.v2)
        self.assert_pids_v2_by_collection(registered, main=None)
        self.assert_no_pid_v2_change(registered)


@override_settings(COLLECTION_ENSURE_NETWORK_CLASSIFICATION=True)
class RegisterCompletesNetworkClassificationTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """
    coleções sem network_classification: o registro completa o dado
    (articlemeta) antes de identificar a coleção principal
    """

    def setUp(self):
        super().setUp()
        Collection.objects.update(network_classification=None)
        cache.delete(ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY)
        self.addCleanup(cache.delete, ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY)
        patcher = patch(
            "collection.models.fetch_data",
            return_value=[
                {"acron": "scl", "network_classification": ["scielonetwork"]},
                {"acron": "psi", "network_classification": ["thematic"]},
            ],
        )
        self.mock_fetch_data = patcher.start()
        self.addCleanup(patcher.stop)

    def test_main_collection_is_identified(self):
        first = self.register(psi_xml(), "psi")
        second = self.register(scl_xml(), "scl")

        # consulta o articlemeta somente uma vez
        self.mock_fetch_data.assert_called_once()
        self.assertTrue(
            Collection.objects.get(acron3="scl").is_national_journal_collection
        )
        self.assertFalse(
            Collection.objects.get(acron3="psi").is_national_journal_collection
        )

        registered = self.assert_same_article_registered_once(first, second)
        self.assertEqual(registered.v2, SCL_V2)
        self.assert_pids_v2_by_collection(registered)
        self.assert_current_version_is_from(registered, self.scl)


class RegisterWithoutCollectionInXMLTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """XML não informa a coleção de origem"""

    def test_no_version_is_registered(self):
        response = self.register(make_xml_with_pre(SCL_V2, "pusp"), "scl")

        registered = PidProviderXML.objects.get()
        self.assertEqual(response["v2"], SCL_V2)
        self.assertEqual(
            set(registered.collections.values_list("acron3", flat=True)),
            {"scl", "psi"},
        )
        self.assertFalse(CollectionPidV2.objects.exists())
        self.assertIsNone(registered.current_version)
        self.assertFalse(XMLVersion.objects.exists())


class XMLVersionByCollectionTest(RegisterSameArticleInDifferentCollectionsTestBase):
    """
    O XML de cada coleção chega em momentos diferentes na migração:
    cada coleção tem sua versão atual e a versão atual do documento é a da
    coleção principal
    """

    def test_each_collection_has_its_own_current_version(self):
        self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        registered = PidProviderXML.objects.get()
        scl_version = self.collection_current_version(registered, self.scl)
        psi_version = self.collection_current_version(registered, self.psi)
        self.assertNotEqual(scl_version, psi_version)
        self.assertEqual(scl_version.xml_with_pre.v2, SCL_V2)
        self.assertEqual(psi_version.xml_with_pre.v2, PSI_V2)
        self.assertEqual(scl_version.xml_with_pre.collection, "scl")
        self.assertEqual(psi_version.xml_with_pre.collection, "psi")

    def test_current_version_is_the_main_collection_version(self):
        self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        registered = PidProviderXML.objects.get()
        self.assert_current_version_is_from(registered, self.scl)
        self.assertEqual(registered.xml_with_pre.v2, SCL_V2)

    def test_main_collection_version_becomes_current_version(self):
        self.register(psi_xml(), "psi")
        registered = PidProviderXML.objects.get()
        # somente a coleção principal completa current_version
        self.assertIsNone(registered.current_version)
        self.assertIsNotNone(self.collection_current_version(registered, self.psi))

        self.register(scl_xml(), "scl")

        self.assert_current_version_is_from(registered, self.scl)

    def test_same_xml_of_the_collection_is_skipped(self):
        self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        total = XMLVersion.objects.count()

        responses = [self.register(scl_xml(), "scl"), self.register(psi_xml(), "psi")]

        self.assertEqual(
            [response["event_status"] for response in responses],
            ["skipped", "skipped"],
        )
        self.assertEqual(XMLVersion.objects.count(), total)

    def test_is_registered_compares_with_version_of_the_same_collection(self):
        response = self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        # XML com o pid v3 atribuído (como no pacote após o registro)
        for xml_with_pre in (scl_xml(), psi_xml()):
            xml_with_pre.v3 = response["v3"]
            with self.subTest(v2=xml_with_pre.v2):
                self.assertTrue(
                    PidProviderXML.is_registered(xml_with_pre)["is_equal"]
                )

    def test_get_xml_with_pre_by_collection(self):
        response = self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")
        v3 = response["v3"]

        self.assertEqual(PidProviderXML.get_xml_with_pre(v3).v2, SCL_V2)
        self.assertEqual(PidProviderXML.get_xml_with_pre(v3, self.scl).v2, SCL_V2)
        self.assertEqual(PidProviderXML.get_xml_with_pre(v3, self.psi).v2, PSI_V2)
        self.assertEqual(
            PidProviderXML.get_xml_with_pre(v3, collection_acron="psi").v2, PSI_V2
        )

    def test_get_xml_with_pre_of_collection_without_version(self):
        response = self.register(scl_xml(), "scl")

        self.assertIsNone(PidProviderXML.get_xml_with_pre(response["v3"], self.psi))


class XMLVersionWithoutMainCollectionTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    def setUp(self):
        super().setUp()
        Collection.objects.update(network_classification=None)

    def test_current_version_is_not_registered(self):
        self.register(psi_xml(), "psi")
        self.register(scl_xml(), "scl")

        registered = PidProviderXML.objects.get()
        # sem coleção principal, current_version não é completado
        self.assertIsNone(registered.current_version)
        self.assertIsNone(PidProviderXML.get_xml_with_pre(registered.v3))
        self.assertEqual(
            PidProviderXML.get_xml_with_pre(registered.v3, self.psi).v2, PSI_V2
        )
        self.assertEqual(
            PidProviderXML.get_xml_with_pre(registered.v3, self.scl).v2, SCL_V2
        )

    def test_update_of_the_same_collection_updates_its_version(self):
        self.register(psi_xml(), "psi")
        self.register(scl_xml(), "scl")
        updated = updated_xml(PSI_V2, "psicousp", "psi")

        self.register(updated, "psi")

        registered = PidProviderXML.objects.get()
        self.assertEqual(
            registered.get_current_version(self.psi).finger_print,
            updated.finger_print,
        )
        self.assertNotEqual(
            registered.get_current_version(self.scl).finger_print,
            updated.finger_print,
        )


class XMLVersionOfJournalWithSameDataInCollectionsTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """
    Periódico com o mesmo PID e acrônimo em todas as coleções: o XML de
    cada coleção difere somente na coleção de origem
    """

    def setUp(self):
        super().setUp()
        SciELOJournal.objects.filter(collection=self.psi).update(
            issn_scielo=ISSN_PRINT, journal_acron="pusp"
        )

    def test_each_collection_is_registered_when_its_xml_arrives(self):
        self.register(scl_xml(), "scl")

        registered = PidProviderXML.objects.get()
        self.assertEqual(registered.collections.count(), 2)
        self.assertEqual(registered.collection_pids_v2_data, [SCL_DATA])

        self.register(make_xml_with_pre(SCL_V2, "pusp", "psi"), "psi")

        registered = PidProviderXML.objects.get()
        self.assertEqual(
            {
                (item.collection.acron3, item.pid_v2, item.current_version.xml_with_pre.collection)
                for item in CollectionPidV2.objects.all()
            },
            {("scl", SCL_V2, "scl"), ("psi", SCL_V2, "psi")},
        )
        self.assert_current_version_is_from(registered, self.scl)
        self.assert_no_pid_v2_change(registered)


class XMLVersionOfJournalWithDifferentAcronInCollectionsTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """
    Periódico com o mesmo PID, mas acrônimos diferentes nas coleções
    (no site novo, o acrônimo é a chave do periódico): o XML de cada
    coleção difere no journal-id
    """

    def setUp(self):
        super().setUp()
        SciELOJournal.objects.filter(collection=self.psi).update(issn_scielo=ISSN_PRINT)

    def test_different_article_pid_v2_with_same_journal_pid(self):
        # pid v2 do artigo depende também do pid do fascículo e da ordem
        psi_v2 = "S0103-65642009000300007"
        self.register(make_xml_with_pre(SCL_V2, "pusp", "scl"), "scl")
        self.register(make_xml_with_pre(psi_v2, "psicousp", "psi"), "psi")

        registered = PidProviderXML.objects.get()
        self.assertEqual(registered.v2, SCL_V2)
        self.assert_no_pid_v2_change(registered)
        self.assertCountEqual(
            registered.collection_pids_v2_data,
            [SCL_DATA, pid_v2_data(psi_v2, "psicousp", "psi", False)],
        )
        self.assertEqual(
            PidProviderXML.get_xml_with_pre(registered.v3, self.psi).v2, psi_v2
        )
        self.assertEqual(
            PidProviderXML.get_xml_with_pre(registered.v3, self.scl).v2, SCL_V2
        )

    def test_same_pid_v2_with_different_journal_acron(self):
        self.register(make_xml_with_pre(SCL_V2, "pusp", "scl"), "scl")
        self.register(make_xml_with_pre(SCL_V2, "psicousp", "psi"), "psi")

        registered = PidProviderXML.objects.get()
        self.assertEqual(registered.v2, SCL_V2)
        self.assertEqual(
            {
                (item.collection.acron3, item.journal_acron, item.pid_v2)
                for item in CollectionPidV2.objects.all()
            },
            {("scl", "pusp", SCL_V2), ("psi", "psicousp", SCL_V2)},
        )
        self.assertEqual(
            PidProviderXML.get_xml_with_pre(registered.v3, self.psi).journal_acron,
            "psicousp",
        )
        self.assertEqual(
            PidProviderXML.get_xml_with_pre(registered.v3, self.scl).journal_acron,
            "pusp",
        )


class MigrationCollectionVersionsTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """
    Migração: o XML de cada coleção (pid v2 e journal-id da coleção)
    cria / atualiza somente a versão desta coleção
    """

    def assert_collection_xml(self, registered, collection, acron, pid_v2):
        xml_with_pre = PidProviderXML.get_xml_with_pre(registered.v3, collection)
        self.assertEqual(xml_with_pre.journal_acron, acron)
        self.assertEqual(xml_with_pre.v2, pid_v2)
        self.assertEqual(xml_with_pre.v3, registered.v3)
        self.assertEqual(xml_with_pre.collection, collection.acron3)
        return xml_with_pre

    def test_other_collections_are_registered_when_their_xml_arrives(self):
        self.register(scl_xml(), "scl")

        registered = PidProviderXML.objects.get()
        self.assertFalse(
            CollectionPidV2.objects.filter(collection=self.psi).exists()
        )

        self.register(psi_xml(), "psi")

        self.assert_collection_xml(registered, self.scl, "pusp", SCL_V2)
        self.assert_collection_xml(registered, self.psi, "psicousp", PSI_V2)

    def test_xml_of_a_collection_updates_only_its_version(self):
        self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        self.register(updated_xml(SCL_V2, "pusp", "scl"), "scl")

        registered = PidProviderXML.objects.get()
        scl = self.assert_collection_xml(registered, self.scl, "pusp", SCL_V2)
        psi = self.assert_collection_xml(registered, self.psi, "psicousp", PSI_V2)
        self.assertIn(UPDATED_TITLE, scl.tostring())
        self.assertNotIn(UPDATED_TITLE, psi.tostring())
        self.assert_current_version_is_from(registered, self.scl)

    def test_xml_collection_is_identified_by_custom_meta(self):
        self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")

        # acrônimo não corresponde a nenhuma coleção
        self.register(updated_xml(SCL_V2, "psicologiausp", "scl"), "scl")

        registered = PidProviderXML.objects.get()
        scl = self.assert_collection_xml(registered, self.scl, "psicologiausp", SCL_V2)
        psi = self.assert_collection_xml(registered, self.psi, "psicousp", PSI_V2)
        self.assertIn(UPDATED_TITLE, scl.tostring())
        self.assertNotIn(UPDATED_TITLE, psi.tostring())

    def test_same_xml_is_skipped(self):
        first = scl_xml()
        self.register(first, "scl")
        total = XMLVersion.objects.count()

        again = scl_xml()
        again.v3 = first.v3
        response = self.register(again, "scl")

        self.assertEqual(response["event_status"], "skipped")
        self.assertEqual(XMLVersion.objects.count(), total)


class ErratumInDifferentCollectionsTest(
    RegisterSameArticleInDifferentCollectionsTestBase
):
    """
    A errata não é uma nova versão do artigo: é outro documento, com pid v2
    próprio, que aponta para o artigo corrigido (related-article).
    Registrar a errata não altera o registro do artigo.
    """

    def setUp(self):
        super().setUp()
        self.register(scl_xml(), "scl")
        self.register(psi_xml(), "psi")
        self.article = PidProviderXML.objects.get()

    def get_erratum(self):
        return PidProviderXML.objects.exclude(pk=self.article.pk).get()

    def test_erratum_is_registered_as_another_document(self):
        response = self.register(
            erratum_xml(SCL_ERRATUM_V2, "pusp", "scl"), "scl"
        )

        self.assertEqual(PidProviderXML.objects.count(), 2)
        erratum = self.get_erratum()
        self.assertEqual(response["v3"], erratum.v3)
        self.assertNotEqual(erratum.v3, self.article.v3)
        self.assertEqual(erratum.v2, SCL_ERRATUM_V2)

    def test_erratum_of_both_collections_is_registered_once(self):
        first = self.register(erratum_xml(SCL_ERRATUM_V2, "pusp", "scl"), "scl")
        second = self.register(
            erratum_xml(PSI_ERRATUM_V2, "psicousp", "psi"), "psi"
        )

        self.assertEqual(PidProviderXML.objects.count(), 2)
        erratum = self.get_erratum()
        self.assertEqual(first["v3"], erratum.v3)
        self.assertEqual(second["v3"], erratum.v3)
        self.assertEqual(erratum.v2, SCL_ERRATUM_V2)
        self.assertCountEqual(
            erratum.collection_pids_v2_data,
            [
                pid_v2_data(SCL_ERRATUM_V2, "pusp", "scl", True),
                pid_v2_data(PSI_ERRATUM_V2, "psicousp", "psi", False),
            ],
        )
        self.assert_no_pid_v2_change(erratum)

    def test_erratum_does_not_change_the_article(self):
        article_versions = {
            collection.acron3: self.collection_current_version(
                self.article, collection
            ).pk
            for collection in (self.scl, self.psi)
        }

        self.register(erratum_xml(SCL_ERRATUM_V2, "pusp", "scl"), "scl")
        self.register(erratum_xml(PSI_ERRATUM_V2, "psicousp", "psi"), "psi")

        self.article.refresh_from_db()
        self.assertEqual(self.article.v2, SCL_V2)
        self.assert_pids_v2_by_collection(self.article)
        self.assert_no_pid_v2_change(self.article)
        self.assertEqual(
            {
                collection.acron3: self.collection_current_version(
                    self.article, collection
                ).pk
                for collection in (self.scl, self.psi)
            },
            article_versions,
        )
