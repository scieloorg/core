"""
Testes de unidade para periódicos presentes em mais de uma coleção com
dados diferentes (PID e/ou acrônimo) e, consequentemente, artigos com
PIDs v2 e XML diferentes em cada coleção.

Ex.: Psicologia USP
- scl: acron=pusp, pid=0103-6564, artigo S0103-65642009000300003
- psi: acron=psicousp, pid=1678-5177, artigo S1678-51772009000300003

Os cenários de registro com XML real estão em
test_register_multi_collection.py
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from collection.models import Collection
from journal.models import Journal, OfficialJournal, SciELOJournal
from pid_provider import exceptions
from pid_provider.models import CollectionPidV2, PidProviderXML, XMLVersion
from pid_provider.multi_collection import (
    get_journal_pid_from_v2,
    get_xml_categorized_collections,
    get_xml_collection_acron,
)
from pid_provider.query_params import compare

User = get_user_model()

SCL_V2 = "S0103-65642009000300003"
PSI_V2 = "S1678-51772009000300003"
ISSN_PRINT = "0103-6564"
ISSN_ELECTRONIC = "1678-5177"

# CollectionPidV2.data
SCL_DATA = {
    "pid_v2": SCL_V2,
    "journal_acron": "pusp",
    "collection_acron": "scl",
    "is_main": True,
}
PSI_DATA = {
    "pid_v2": PSI_V2,
    "journal_acron": "psicousp",
    "collection_acron": "psi",
    "is_main": False,
}


def make_xml_with_pre(
    v2=None,
    journal_acron=None,
    collection=None,
    issn_print=ISSN_PRINT,
    issn_electronic=ISSN_ELECTRONIC,
):
    return SimpleNamespace(
        v2=v2,
        v3="V3-PSICOUSP-0000000001",
        aop_pid=None,
        is_aop=False,
        journal_acron=journal_acron,
        collection=collection,
        journal_issn_print=issn_print,
        journal_issn_electronic=issn_electronic,
    )


class MultiCollectionJournalTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="multicol", password="x")
        self.scl = Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=self.user
        )
        self.psi = Collection.objects.create(
            acron3="psi", network_classification=["thematic"], creator=self.user
        )
        journal = Journal.objects.create(
            official=OfficialJournal.objects.create(
                title="Psicologia USP",
                issn_print=ISSN_PRINT,
                issn_electronic=ISSN_ELECTRONIC,
                creator=self.user,
            ),
            creator=self.user,
        )
        # psi é criada antes de scl para verificar que a principal vem primeiro
        for collection, acron, pid in (
            (self.psi, "psicousp", ISSN_ELECTRONIC),
            (self.scl, "pusp", ISSN_PRINT),
        ):
            SciELOJournal.objects.create(
                journal=journal,
                collection=collection,
                journal_acron=acron,
                issn_scielo=pid,
                creator=self.user,
            )

    def create_pid_provider_xml(self, v2=SCL_V2):
        return PidProviderXML.objects.create(
            v3="V3-PSICOUSP-0000000001", v2=v2, creator=self.user
        )

    def create_version(self, registered, finger_print):
        return XMLVersion.objects.create(
            pid_provider_xml=registered,
            finger_print=finger_print,
            creator=self.user,
        )

    def create_collection_version(
        self, registered, finger_print, collection, pid_v2, journal_acron
    ):
        version = self.create_version(registered, finger_print)
        CollectionPidV2.create_or_update(
            self.user,
            registered,
            collection,
            pid_v2,
            journal_acron=journal_acron,
            current_version=version,
        )
        return version


class GetJournalPidFromV2Test(SimpleTestCase):
    def test_get_journal_pid_from_v2(self):
        self.assertEqual(get_journal_pid_from_v2(SCL_V2), ISSN_PRINT)
        self.assertEqual(get_journal_pid_from_v2(PSI_V2), ISSN_ELECTRONIC)
        self.assertIsNone(get_journal_pid_from_v2(None))
        self.assertIsNone(get_journal_pid_from_v2("S0103-6564"))


class GetXMLCategorizedCollectionsTest(MultiCollectionJournalTestBase):
    def result(self, xml_with_pre, key="items"):
        return {
            (item["collection_acron"], item["journal_acron"], item["journal_pid"])
            for item in get_xml_categorized_collections(xml_with_pre)[key]
        }

    def test_returns_journal_data_by_collection(self):
        # psi pelo PID do periódico contido no pid v2, scl pelo acrônimo
        xml_with_pre = make_xml_with_pre(PSI_V2, "pusp")
        self.assertEqual(
            self.result(xml_with_pre),
            {("scl", "pusp", ISSN_PRINT), ("psi", "psicousp", ISSN_ELECTRONIC)},
        )
        # nenhuma com o PID e o acrônimo do XML
        self.assertEqual(self.result(xml_with_pre, "matched_items"), set())

    def test_matched_items_have_the_journal_pid_and_acron_of_the_xml(self):
        self.assertEqual(
            self.result(make_xml_with_pre(PSI_V2, "psicousp"), "matched_items"),
            {("psi", "psicousp", ISSN_ELECTRONIC)},
        )

    def test_issn_does_not_identify_the_journal(self):
        # os ISSNs são comuns às coleções: somente PID e acrônimo
        self.assertEqual(
            self.result(make_xml_with_pre(PSI_V2, "psicousp")),
            {("psi", "psicousp", ISSN_ELECTRONIC)},
        )

    def test_identifies_journal_by_pid_v2_or_acron(self):
        # sem ISSN, somente a coleção com o PID ou o acrônimo do periódico
        expected = {("psi", "psicousp", ISSN_ELECTRONIC)}
        cases = (
            # somente pelo PID do periódico contido no pid v2
            make_xml_with_pre(PSI_V2, issn_print=None, issn_electronic=None),
            # pelo acrônimo, PID do periódico desconhecido
            make_xml_with_pre(
                "S0000-00002009000300003",
                "psicousp",
                issn_print=None,
                issn_electronic=None,
            ),
        )
        for xml_with_pre in cases:
            with self.subTest(v2=xml_with_pre.v2, acron=xml_with_pre.journal_acron):
                self.assertEqual(self.result(xml_with_pre), expected)

    def test_empty_without_journal_identification(self):
        # sem pid v2 e sem acrônimo, mesmo com ISSN
        self.assertEqual(
            get_xml_categorized_collections(make_xml_with_pre(None, None)),
            {"items": [], "matched_items": []},
        )

    def test_empty_when_journal_is_not_found(self):
        xml_with_pre = make_xml_with_pre(
            "S0000-00002009000300003",
            "xxx",
            issn_print="0000-0000",
            issn_electronic="0000-0001",
        )
        self.assertEqual(self.result(xml_with_pre), set())


class GetXMLCollectionAcronTest(MultiCollectionJournalTestBase):
    """
    Coleção do XML que não a informa: a que tem os mesmos PID (contido no
    pid v2) e acrônimo do periódico
    """

    def test_single_match(self):
        for v2, acron, expected in (
            (SCL_V2, "pusp", "scl"),
            (PSI_V2, "psicousp", "psi"),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(
                    get_xml_collection_acron(make_xml_with_pre(v2, acron)), expected
                )

    def test_no_match(self):
        for v2, acron in (
            # PID de psi e acrônimo de scl
            (PSI_V2, "pusp"),
            # sem pid v2 ou sem acrônimo
            (None, "pusp"),
            (SCL_V2, None),
        ):
            with self.subTest(v2=v2, acron=acron):
                self.assertIsNone(
                    get_xml_collection_acron(make_xml_with_pre(v2, acron))
                )

    def test_multiple_matches_is_an_error(self):
        # mesmos PID e acrônimo do periódico em outra coleção, mesmo sendo
        # scl a principal
        xyz = Collection.objects.create(
            acron3="xyz", network_classification=["thematic"], creator=self.user
        )
        SciELOJournal.objects.create(
            journal=SciELOJournal.objects.get(collection=self.scl).journal,
            collection=xyz,
            journal_acron="pusp",
            issn_scielo=ISSN_PRINT,
            creator=self.user,
        )
        with self.assertRaises(
            exceptions.MultipleCollectionsMatchedErrorToGetPidProviderXMLError
        ):
            get_xml_collection_acron(make_xml_with_pre(SCL_V2, "pusp"))


class CurrentVersionByCollectionTest(MultiCollectionJournalTestBase):
    def test_get_current_version(self):
        registered = self.create_pid_provider_xml()
        psi_version = self.create_collection_version(
            registered, "psi", self.psi, PSI_V2, "psicousp"
        )

        # sem versão da coleção principal: a mais recente das coleções
        self.assertEqual(registered.get_current_version(), psi_version)
        # documento com versão por coleção: sem a da coleção solicitada
        self.assertIsNone(registered.get_current_version(self.scl))
        self.assertEqual(registered.get_current_version(self.psi), psi_version)
        self.assertEqual(
            registered.get_current_version(collection_acron="psi"), psi_version
        )

        registered.current_version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2, "pusp"
        )
        registered.save()
        self.assertEqual(registered.get_current_version(), registered.current_version)
        self.assertEqual(
            registered.get_current_version(self.scl), registered.current_version
        )
        self.assertIsNone(PidProviderXML().get_current_version(self.psi))

    def test_current_version_of_collection_is_the_last_registered(self):
        registered = self.create_pid_provider_xml()
        self.create_collection_version(registered, "psi-1", self.psi, PSI_V2, "psicousp")
        second = self.create_collection_version(
            registered, "psi-2", self.psi, PSI_V2, "psicousp"
        )
        # versão sem coleção não é versão de coleção
        self.create_version(registered, None)

        self.assertEqual(registered.get_current_version(self.psi), second)
        # um único registro por coleção
        self.assertEqual(registered.collection_pids_v2.count(), 1)

    def test_collection_pids_v2_data(self):
        registered = self.create_pid_provider_xml()
        self.create_collection_version(registered, "scl", self.scl, SCL_V2, "pusp")
        self.create_collection_version(registered, "psi", self.psi, PSI_V2, "psicousp")
        self.create_version(registered, None)

        self.assertCountEqual(
            registered.collection_pids_v2_data, [SCL_DATA, PSI_DATA]
        )

    def test_is_equal_to_compares_with_version_of_the_same_collection(self):
        registered = self.create_pid_provider_xml()
        self.create_collection_version(registered, "psi", self.psi, PSI_V2, "psicousp")

        with patch.object(XMLVersion, "is_equal_to", return_value=True) as is_equal:
            self.assertTrue(
                registered.is_equal_to(make_xml_with_pre(collection="psi"))
            )
            self.assertEqual(is_equal.call_count, 1)
            self.assertFalse(
                registered.is_equal_to(make_xml_with_pre(collection="scl"))
            )
            self.assertFalse(
                registered.is_equal_to(make_xml_with_pre(collection=None))
            )
            self.assertFalse(
                PidProviderXML().is_equal_to(make_xml_with_pre(collection="psi"))
            )
            self.assertEqual(is_equal.call_count, 1)


class PidProviderXMLCollectionsTest(MultiCollectionJournalTestBase):
    def test_add_collections_registers_only_the_xml_collection(self):
        registered = self.create_pid_provider_xml(PSI_V2)
        xml_with_pre = make_xml_with_pre(PSI_V2, "psicousp", collection="psi")
        xml_adapter = MagicMock(xml_with_pre=xml_with_pre)
        version = self.create_version(registered, "psi")

        with patch.object(
            XMLVersion, "get_or_create", return_value=version
        ) as get_or_create:
            registered.add_collections(self.user, xml_adapter, self.psi)

        get_or_create.assert_called_once_with(self.user, registered, xml_with_pre)
        registered.refresh_from_db()
        # somente a coleção do XML
        self.assertEqual(
            set(registered.collections.values_list("acron3", flat=True)),
            {"psi"},
        )
        self.assertEqual(registered.collection_pids_v2_data, [PSI_DATA])
        self.assertEqual(registered.get_current_version(self.psi), version)
        # current_version vazio é completado com a versão do XML recebido
        self.assertEqual(registered.current_version, version)

    def test_add_collections_main_collection_xml_is_the_current_version(self):
        registered = self.create_pid_provider_xml(None)
        xml_adapter = MagicMock(
            xml_with_pre=make_xml_with_pre(SCL_V2, "pusp", collection="scl")
        )
        version = self.create_version(registered, "scl")

        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(self.user, xml_adapter, self.scl)

        registered.refresh_from_db()
        self.assertEqual(registered.current_version, version)
        self.assertEqual(registered.v2, SCL_V2)
        self.assertEqual(registered.get_current_version(self.scl), version)
        self.assertEqual(registered.collection_pids_v2_data, [SCL_DATA])

    def test_add_collections_other_collection_keeps_the_main_data(self):
        # documento em mais de uma coleção: XML da que não é nacional não
        # altera v2 e current_version
        registered = self.create_pid_provider_xml(SCL_V2)
        main_version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2, "pusp"
        )
        registered.current_version = main_version
        registered.save()
        xml_adapter = MagicMock(
            xml_with_pre=make_xml_with_pre(PSI_V2, "psicousp", collection="psi")
        )
        version = self.create_version(registered, "psi")

        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(self.user, xml_adapter, self.psi)

        registered.refresh_from_db()
        self.assertEqual(registered.v2, SCL_V2)
        self.assertEqual(registered.current_version, main_version)
        self.assertCountEqual(
            registered.collection_pids_v2_data, [SCL_DATA, PSI_DATA]
        )

    def test_add_collections_the_only_collection_updates_current_version(self):
        # documento em uma única coleção: o XML dela atualiza v2 e
        # current_version, mesmo sendo temática
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.current_version = self.create_version(registered, "previous")
        registered.save()
        xml_adapter = MagicMock(
            xml_with_pre=make_xml_with_pre(PSI_V2, "psicousp", collection="psi")
        )
        version = self.create_version(registered, "psi")

        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(self.user, xml_adapter, self.psi)

        registered.refresh_from_db()
        self.assertEqual(registered.v2, PSI_V2)
        self.assertEqual(registered.current_version, version)

    def test_add_collections_without_xml_collection(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        xml_adapter = MagicMock(xml_with_pre=make_xml_with_pre(SCL_V2, "pusp"))

        version = self.create_version(registered, "no-collection")
        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(self.user, xml_adapter, None)

        registered.refresh_from_db()
        self.assertEqual(registered.collections.count(), 0)
        # coleção desconhecida: sem versão por coleção, mas current_version
        # não fica vazio
        self.assertFalse(registered.collection_pids_v2.exists())
        self.assertEqual(registered.current_version, version)
        self.assertEqual(registered.v2, SCL_V2)

    def test_add_current_version_replaces_the_current_version(self):
        # ex.: fix_pid_v2
        registered = self.create_pid_provider_xml(SCL_V2)
        old_version = self.create_version(registered, "scl")
        registered.current_version = old_version
        registered.save()
        xml_with_pre = make_xml_with_pre(SCL_V2, "pusp", collection="scl")
        new_version = self.create_version(registered, "scl-fixed")

        with patch.object(
            XMLVersion, "get_or_create", return_value=new_version
        ) as get_or_create:
            registered._add_current_version(xml_with_pre, self.user, delete=True)

        get_or_create.assert_called_once_with(self.user, registered, xml_with_pre)
        self.assertEqual(registered.current_version, new_version)
        self.assertFalse(XMLVersion.objects.filter(pk=old_version.pk).exists())


class DataToCompareTest(MultiCollectionJournalTestBase):
    def test_uses_all_pids_v2_when_unreadable(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        for collection, pid_v2, acron in (
            (self.scl, SCL_V2, "pusp"),
            (self.psi, PSI_V2, "psicousp"),
        ):
            self.create_collection_version(
                registered, pid_v2, collection, pid_v2, acron
            )
        self.assertEqual(registered.pid_v2_list, [SCL_V2, PSI_V2])

        with patch.object(PidProviderXML, "get_readable_data", return_value={}):
            registered_data = registered.data_to_compare
        self.assertEqual(registered_data["pid_v2"], [SCL_V2, PSI_V2])

        result = compare(registered_data, {**registered_data, "pid_v2": PSI_V2})
        pid_v2_item = next(i for i in result["items"] if i["label"] == "pid_v2")
        self.assertEqual(pid_v2_item["score"], 1)


class ReasonsToUpdateTest(MultiCollectionJournalTestBase):
    """
    XML idêntico ao registrado é registrado novamente se os dados por
    coleção estão incompletos ou divergentes (ex.: documentos registrados
    antes de CollectionPidV2)
    """

    def reasons(self, registered, xml_with_pre):
        return registered.get_reasons_to_update(
            xml_with_pre, PidProviderXML.get_xml_collection(xml_with_pre)
        )

    def create_complete(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.collections.add(self.scl, self.psi)
        scl_version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2, "pusp"
        )
        self.create_collection_version(registered, "psi", self.psi, PSI_V2, "psicousp")
        registered.current_version = scl_version
        registered.save()
        return registered

    def test_complete_registration_has_no_reasons(self):
        registered = self.create_complete()
        for xml_with_pre in (
            make_xml_with_pre(SCL_V2, "pusp", collection="scl"),
            make_xml_with_pre(PSI_V2, "psicousp", collection="psi"),
        ):
            with self.subTest(xml_with_pre.collection):
                self.assertEqual(self.reasons(registered, xml_with_pre), [])

    def test_article_absent_from_other_journal_collection(self):
        # periódico em scl e psi, artigo somente em scl (periódico não aceito
        # ou desindexado em psi)
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.collections.add(self.scl, self.psi)
        version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2, "pusp"
        )
        registered.current_version = version
        registered.save()

        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
            [],
        )

    def test_other_collection_without_version_is_not_a_reason(self):
        registered = self.create_complete()
        registered.collection_pids_v2.filter(collection=self.psi).update(
            current_version=None
        )
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
            [],
        )

    def test_missing_xml_collection(self):
        registered = self.create_complete()
        registered.collections.remove(self.psi)
        # somente a coleção do XML é exigida
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
            [],
        )
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(PSI_V2, "psicousp", collection="psi")),
            ["missing_xml_collection"],
        )

    def test_collection_pid_v2_differs_from_xml(self):
        registered = self.create_complete()
        registered.collection_pids_v2.filter(collection=self.psi).update(
            pid_v2="S1678-51772009000300099"
        )
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(PSI_V2, "psicousp", collection="psi")),
            ["collection_pid_v2_differs"],
        )

    def test_national_collection_xml_and_v2_of_another_collection(self):
        # ex.: registro existente da instância do Brasil com os dados de psi
        registered = self.create_complete()
        registered.v2 = PSI_V2
        registered.current_version = registered.get_current_version(self.psi)
        registered.save()

        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
            ["current_version_differs"],
        )
        # documento em mais de uma coleção: XML da que não é nacional não
        # exige v2 e current_version dela
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(PSI_V2, "psicousp", collection="psi")),
            [],
        )

    def test_empty_v2_and_current_version(self):
        registered = self.create_complete()
        PidProviderXML.objects.filter(pk=registered.pk).update(
            v2=None, current_version=None
        )
        registered.refresh_from_db()
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(PSI_V2, "psicousp", collection="psi")),
            ["missing_v2", "missing_current_version"],
        )

    def test_unregistered_or_without_xml_collection(self):
        xml_with_pre = make_xml_with_pre(SCL_V2, "pusp", collection="scl")
        self.assertEqual(
            PidProviderXML().get_reasons_to_update(xml_with_pre, self.scl), []
        )
        self.assertEqual(
            self.create_complete().get_reasons_to_update(xml_with_pre, None), []
        )


class IsUpdatedWithCollectionsTest(MultiCollectionJournalTestBase):
    def is_updated(self, registered, xml_with_pre):
        return PidProviderXML.is_updated(
            xml_with_pre,
            registered,
            force_update=False,
            origin_date=None,
            registered_in_core=None,
            collection=PidProviderXML.get_xml_collection(xml_with_pre),
        )

    def create_registered(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.collections.add(self.scl, self.psi)
        version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2, "pusp"
        )
        registered.current_version = version
        registered.readable_data = {"x": 1}
        registered.save()
        return registered

    @patch.object(XMLVersion, "is_equal_to", return_value=True)
    def test_equal_xml_of_article_absent_from_other_collection_is_skipped(
        self, is_equal
    ):
        registered = self.create_registered()
        # artigo somente em scl (periódico não aceito ou desindexado em psi):
        # ignora o XML idêntico de scl
        with self.assertRaises(exceptions.SkipSavePidProviderXML):
            self.is_updated(
                registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")
            )

    @patch.object(XMLVersion, "is_equal_to", return_value=True)
    def test_equal_xml_with_incomplete_collection_data_is_updated(self, is_equal):
        registered = self.create_registered()
        registered.collections.remove(self.scl)
        # coleção do XML ausente: não ignora o XML idêntico de scl
        self.assertIsNone(
            self.is_updated(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl"))
        )

    @patch.object(XMLVersion, "is_equal_to", return_value=True)
    def test_xml_without_collection_is_not_equal(self, is_equal):
        registered = self.create_registered()
        # sem a coleção do XML, não há versão da coleção para comparar
        self.assertIsNone(self.is_updated(registered, make_xml_with_pre(SCL_V2, "pusp")))


class GetPidV2Test(MultiCollectionJournalTestBase):
    """pid v2 do documento na coleção (ver complete_missing_xml_pids)"""

    def test_pid_v2_of_the_collection(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        self.create_collection_version(registered, "scl", self.scl, SCL_V2, "pusp")
        self.create_collection_version(
            registered, "psi", self.psi, PSI_V2, "psicousp"
        )

        self.assertEqual(registered.get_pid_v2(), SCL_V2)
        self.assertEqual(registered.get_pid_v2("scl"), SCL_V2)
        self.assertEqual(registered.get_pid_v2("psi"), PSI_V2)

    def test_pid_v2_of_other_collection_is_not_returned(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        self.create_collection_version(registered, "scl", self.scl, SCL_V2, "pusp")

        self.assertIsNone(registered.get_pid_v2("psi"))

    def test_pid_v2_of_document_registered_before_collection_pid_v2(self):
        # documento registrado antes de CollectionPidV2
        registered = self.create_pid_provider_xml(SCL_V2)
        self.assertEqual(registered.get_pid_v2("psi"), SCL_V2)
        self.assertEqual(PidProviderXML(v2=SCL_V2).get_pid_v2("psi"), SCL_V2)

