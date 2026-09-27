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
from pid_provider.models import CollectionPidV2, PidProviderXML, XMLVersion
from pid_provider.multi_collection import (
    get_journal_pid_from_v2,
    get_xml_collections,
    normalize_acron,
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
            pid_provider_xml=registered, finger_print=finger_print, creator=self.user
        )

    def create_collection_pid_v2(self, registered, collection, pid_v2, version):
        return CollectionPidV2.create_or_update(
            self.user,
            pid_provider_xml=registered,
            collection=collection,
            pid_v2=pid_v2,
            journal_acron="pusp" if collection == self.scl else "psicousp",
            current_version=version,
        )


class GetJournalPidFromV2Test(SimpleTestCase):
    def test_get_journal_pid_from_v2(self):
        self.assertEqual(get_journal_pid_from_v2(SCL_V2), ISSN_PRINT)
        self.assertEqual(get_journal_pid_from_v2(PSI_V2), ISSN_ELECTRONIC)
        self.assertIsNone(get_journal_pid_from_v2(None))
        self.assertIsNone(get_journal_pid_from_v2("S0103-6564"))


class NormalizeAcronTest(SimpleTestCase):
    def test_normalize_acron(self):
        self.assertEqual(normalize_acron(" PUSP "), "pusp")
        self.assertIsNone(normalize_acron(None))


class GetXMLCollectionsTest(MultiCollectionJournalTestBase):
    def result(self, xml_with_pre):
        return [
            (
                item["collection"].acron3,
                item["journal_acron"],
                item["journal_pid"],
                item["is_main"],
            )
            for item in get_xml_collections(xml_with_pre)
        ]

    def test_returns_journal_data_by_collection_with_main_first(self):
        self.assertEqual(
            self.result(make_xml_with_pre(PSI_V2, "psicousp")),
            [
                ("scl", "pusp", ISSN_PRINT, True),
                ("psi", "psicousp", ISSN_ELECTRONIC, False),
            ],
        )

    def test_identifies_journal_by_pid_v2_or_acron(self):
        # sem ISSN, somente a coleção com o PID ou o acrônimo do periódico
        expected = [("psi", "psicousp", ISSN_ELECTRONIC, False)]
        cases = (
            # somente pelo PID do periódico contido no pid v2
            make_xml_with_pre(PSI_V2, issn_print=None, issn_electronic=None),
            # pelo acrônimo (normalizado), PID do periódico desconhecido
            make_xml_with_pre(
                "S0000-00002009000300003",
                " PSICOUSP ",
                issn_print=None,
                issn_electronic=None,
            ),
        )
        for xml_with_pre in cases:
            with self.subTest(v2=xml_with_pre.v2, acron=xml_with_pre.journal_acron):
                self.assertEqual(self.result(xml_with_pre), expected)

    def test_no_main_collection(self):
        Collection.objects.update(network_classification=None)
        self.assertEqual(
            {item[3] for item in self.result(make_xml_with_pre(SCL_V2, "pusp"))},
            {False},
        )

    def test_empty_without_journal_identification(self):
        xml_with_pre = make_xml_with_pre(
            None, "pusp", issn_print=None, issn_electronic=None
        )
        self.assertEqual(get_xml_collections(xml_with_pre), [])

    def test_empty_when_journal_is_not_found(self):
        xml_with_pre = make_xml_with_pre(
            "S0000-00002009000300003",
            "xxx",
            issn_print="0000-0000",
            issn_electronic="0000-0001",
        )
        self.assertEqual(get_xml_collections(xml_with_pre), [])


class CollectionPidV2Test(MultiCollectionJournalTestBase):
    def test_journal_pid(self):
        self.assertEqual(CollectionPidV2(pid_v2=PSI_V2).journal_pid, ISSN_ELECTRONIC)
        self.assertIsNone(CollectionPidV2().journal_pid)

    def test_create_or_update_requires_all_data(self):
        registered = self.create_pid_provider_xml()
        version = self.create_version(registered, "v1")
        params = dict(
            user=self.user,
            pid_provider_xml=registered,
            collection=self.psi,
            pid_v2=PSI_V2,
            journal_acron="psicousp",
            current_version=version,
        )
        for name in params:
            with self.subTest(missing=name):
                with self.assertRaises(ValueError):
                    CollectionPidV2.create_or_update(**{**params, name: None})
        self.assertFalse(CollectionPidV2.objects.exists())

    def test_create_or_update(self):
        registered = self.create_pid_provider_xml()
        first = self.create_version(registered, "v1")
        second = self.create_version(registered, "v2")

        self.create_collection_pid_v2(registered, self.psi, PSI_V2, first)
        obj = self.create_collection_pid_v2(registered, self.psi, PSI_V2, second)

        obj.refresh_from_db()
        self.assertEqual(obj.current_version, second)
        self.assertEqual(obj.journal_acron, "psicousp")
        self.assertEqual(
            CollectionPidV2.objects.filter(pid_provider_xml=registered).count(), 1
        )

    def test_get_current_version(self):
        registered = self.create_pid_provider_xml()
        psi_version = self.create_version(registered, "psi")
        self.create_collection_pid_v2(registered, self.psi, PSI_V2, psi_version)

        # sem versão da coleção principal
        self.assertIsNone(CollectionPidV2.get_current_version(registered))
        self.assertIsNone(CollectionPidV2.get_current_version(registered, self.scl))
        self.assertEqual(
            CollectionPidV2.get_current_version(registered, self.psi), psi_version
        )
        self.assertEqual(
            CollectionPidV2.get_current_version(registered, collection_acron="psi"),
            psi_version,
        )

        registered.current_version = self.create_version(registered, "scl")
        registered.save()
        self.assertEqual(
            CollectionPidV2.get_current_version(registered),
            registered.current_version,
        )
        self.assertIsNone(CollectionPidV2.get_current_version(None))

    def test_is_equal_to_compares_with_version_of_the_same_collection(self):
        registered = self.create_pid_provider_xml()
        psi_version = self.create_version(registered, "psi")
        self.create_collection_pid_v2(registered, self.psi, PSI_V2, psi_version)

        with patch.object(XMLVersion, "is_equal_to", return_value=True) as is_equal:
            self.assertTrue(
                CollectionPidV2.is_equal_to(registered, make_xml_with_pre(collection="psi"))
            )
            self.assertEqual(is_equal.call_count, 1)
            self.assertFalse(
                CollectionPidV2.is_equal_to(registered, make_xml_with_pre(collection="scl"))
            )
            self.assertFalse(
                CollectionPidV2.is_equal_to(registered, make_xml_with_pre(collection=None))
            )
            self.assertFalse(
                CollectionPidV2.is_equal_to(None, make_xml_with_pre(collection="psi"))
            )
            self.assertEqual(is_equal.call_count, 1)


class PidProviderXMLCollectionsTest(MultiCollectionJournalTestBase):
    def test_get_current_version(self):
        registered = self.create_pid_provider_xml()
        psi_version = self.create_version(registered, "psi")
        self.create_collection_pid_v2(registered, self.psi, PSI_V2, psi_version)
        registered.current_version = self.create_version(registered, "scl")
        registered.save()

        self.assertEqual(registered.get_current_version(), registered.current_version)
        self.assertEqual(registered.get_current_version(self.psi), psi_version)
        self.assertEqual(
            registered.get_current_version(collection_acron="psi"), psi_version
        )
        self.assertIsNone(registered.get_current_version(self.scl))

    def test_add_collections_registers_only_the_xml_collection(self):
        registered = self.create_pid_provider_xml(PSI_V2)
        xml_adapter = MagicMock(
            xml_with_pre=make_xml_with_pre(PSI_V2, "psicousp", collection="psi")
        )
        version = self.create_version(registered, "psi")

        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(self.user, xml_adapter)

        registered.refresh_from_db()
        self.assertEqual(
            set(registered.collections.values_list("acron3", flat=True)),
            {"scl", "psi"},
        )
        self.assertEqual(registered.collection_pids_v2_data, [PSI_DATA])
        self.assertEqual(registered.get_current_version(self.psi), version)
        # somente o XML da coleção principal é a versão atual do documento
        self.assertIsNone(registered.current_version)

    def test_add_collections_main_collection_xml_is_the_current_version(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        xml_adapter = MagicMock(
            xml_with_pre=make_xml_with_pre(SCL_V2, "pusp", collection="scl")
        )
        version = self.create_version(registered, "scl")

        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(self.user, xml_adapter)

        registered.refresh_from_db()
        self.assertEqual(registered.current_version, version)
        self.assertEqual(registered.get_current_version(self.scl), version)

    def test_add_collections_without_xml_collection(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        xml_adapter = MagicMock(xml_with_pre=make_xml_with_pre(SCL_V2, "pusp"))

        with patch.object(XMLVersion, "get_or_create") as get_or_create:
            registered.add_collections(self.user, xml_adapter)

        get_or_create.assert_not_called()
        registered.refresh_from_db()
        self.assertEqual(registered.collections.count(), 2)
        self.assertFalse(registered.collection_pids_v2.exists())
        self.assertIsNone(registered.current_version)

    def test_check_registered_pids_changed_compares_pid_v2_of_the_same_collection(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        self.create_collection_pid_v2(
            registered, self.psi, PSI_V2, self.create_version(registered, "psi")
        )
        cases = (
            # (pid v2 do XML, coleção do XML, houve mudança)
            (PSI_V2, "psi", False),
            ("S1678-51772009000300099", "psi", True),
            # coleção sem pid v2 registrado
            (PSI_V2, "scl", False),
        )
        for pid_v2, collection, expected in cases:
            with self.subTest(pid_v2=pid_v2, collection=collection):
                xml_with_pre = make_xml_with_pre(pid_v2, collection=collection)
                changed = registered.check_registered_pids_changed(xml_with_pre)
                self.assertEqual(
                    any(item["pid_type"] == "pid_v2" for item in changed), expected
                )


class DataToCompareTest(MultiCollectionJournalTestBase):
    def test_uses_all_pids_v2_when_unreadable(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        for collection, pid_v2 in ((self.scl, SCL_V2), (self.psi, PSI_V2)):
            self.create_collection_pid_v2(
                registered, collection, pid_v2, self.create_version(registered, pid_v2)
            )
        self.assertEqual(registered.pid_v2_list, [SCL_V2, PSI_V2])
        self.assertCountEqual(
            registered.collection_pids_v2_data, [SCL_DATA, PSI_DATA]
        )

        with patch.object(PidProviderXML, "get_readable_data", return_value={}):
            registered_data = registered.data_to_compare
        self.assertEqual(registered_data["pid_v2"], [SCL_V2, PSI_V2])

        result = compare(registered_data, {**registered_data, "pid_v2": PSI_V2})
        pid_v2_item = next(i for i in result["items"] if i["label"] == "pid_v2")
        self.assertEqual(pid_v2_item["score"], 1)
