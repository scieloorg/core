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
    get_xml_collection_acron,
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


class GetXMLCollectionAcronTest(SimpleTestCase):
    def xml_collections(self, *items):
        return [
            {
                "collection": SimpleNamespace(acron3=acron3),
                "journal_acron": journal_acron,
                "journal_pid": journal_pid,
                "is_main": is_main,
            }
            for acron3, journal_acron, journal_pid, is_main in items
        ]

    def test_by_journal_pid_of_pid_v2(self):
        xml_collections = self.xml_collections(
            ("scl", "pusp", ISSN_PRINT, True),
            ("psi", "psicousp", ISSN_ELECTRONIC, False),
        )
        for v2, expected in ((SCL_V2, "scl"), (PSI_V2, "psi")):
            with self.subTest(v2=v2):
                self.assertEqual(
                    get_xml_collection_acron(
                        make_xml_with_pre(v2, "pusp"), xml_collections
                    ),
                    expected,
                )

    def test_by_journal_acron_when_journal_pid_is_the_same(self):
        xml_collections = self.xml_collections(
            ("scl", "pusp", ISSN_PRINT, True),
            ("psi", "psicousp", ISSN_PRINT, False),
        )
        self.assertEqual(
            get_xml_collection_acron(
                make_xml_with_pre(SCL_V2, " PSICOUSP "), xml_collections
            ),
            "psi",
        )

    def test_by_journal_acron_when_journal_pid_is_unknown(self):
        xml_collections = self.xml_collections(
            ("scl", "pusp", ISSN_PRINT, True),
            ("psi", "psicousp", ISSN_ELECTRONIC, False),
        )
        self.assertEqual(
            get_xml_collection_acron(
                make_xml_with_pre("S0000-00002009000300003", "psicousp"),
                xml_collections,
            ),
            "psi",
        )

    def test_single_collection(self):
        xml_collections = self.xml_collections(("psi", "psicousp", ISSN_ELECTRONIC, False))
        self.assertEqual(
            get_xml_collection_acron(make_xml_with_pre(None, None), xml_collections),
            "psi",
        )

    def test_none_when_ambiguous(self):
        xml_collections = self.xml_collections(
            ("scl", "pusp", ISSN_PRINT, True),
            ("psi", "pusp", ISSN_PRINT, False),
        )
        self.assertIsNone(
            get_xml_collection_acron(make_xml_with_pre(SCL_V2, "pusp"), xml_collections)
        )
        self.assertIsNone(get_xml_collection_acron(make_xml_with_pre(SCL_V2, "pusp"), []))


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

        # sem versão da coleção principal: a mais recente das coleções
        self.assertEqual(CollectionPidV2.get_current_version(registered), psi_version)
        # documento com versão por coleção: sem a da coleção solicitada
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

    def test_get_current_version_of_document_registered_before_collection_pid_v2(self):
        registered = self.create_pid_provider_xml()
        registered.current_version = self.create_version(registered, "legacy")
        registered.save()

        # legado: nenhuma versão por coleção, usa PidProviderXML.current_version
        for collection in (None, self.scl, self.psi):
            with self.subTest(collection=collection):
                self.assertEqual(
                    CollectionPidV2.get_current_version(registered, collection),
                    registered.current_version,
                )
        self.assertEqual(
            CollectionPidV2.get_current_version(registered, collection_acron="psi"),
            registered.current_version,
        )

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
        self.assertIsNone(PidProviderXML().get_current_version(self.psi))

    def test_add_collections_registers_only_the_xml_collection(self):
        registered = self.create_pid_provider_xml(PSI_V2)
        xml_adapter = MagicMock(
            xml_with_pre=make_xml_with_pre(PSI_V2, "psicousp", collection="psi")
        )
        version = self.create_version(registered, "psi")

        with patch.object(
            XMLVersion, "get_or_create", return_value=version
        ) as get_or_create:
            registered.add_collections(
                self.user, xml_adapter, get_xml_collections(xml_adapter.xml_with_pre)
            )

        get_or_create.assert_called_once_with(
            self.user, registered, xml_adapter.xml_with_pre
        )
        registered.refresh_from_db()
        self.assertEqual(
            set(registered.collections.values_list("acron3", flat=True)),
            {"scl", "psi"},
        )
        self.assertEqual(registered.collection_pids_v2_data, [PSI_DATA])
        self.assertEqual(registered.get_current_version(self.psi), version)
        # current_version vazio é completado com a versão do XML recebido,
        # até que o XML da coleção principal seja registrado
        self.assertEqual(registered.current_version, version)

    def test_add_collections_main_collection_xml_is_the_current_version(self):
        registered = self.create_pid_provider_xml(None)
        xml_adapter = MagicMock(
            xml_with_pre=make_xml_with_pre(SCL_V2, "pusp", collection="scl")
        )
        version = self.create_version(registered, "scl")

        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(
                self.user, xml_adapter, get_xml_collections(xml_adapter.xml_with_pre)
            )

        registered.refresh_from_db()
        self.assertEqual(registered.current_version, version)
        self.assertEqual(registered.v2, SCL_V2)
        self.assertEqual(registered.get_current_version(self.scl), version)
        self.assertEqual(registered.collection_pids_v2_data, [SCL_DATA])

    def test_add_collections_without_xml_collection(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        # mesmo PID e acrônimo do periódico nas coleções: coleção do XML
        # não identificada (ver get_xml_collection_acron)
        SciELOJournal.objects.filter(collection=self.psi).update(
            issn_scielo=ISSN_PRINT, journal_acron="pusp"
        )
        xml_adapter = MagicMock(xml_with_pre=make_xml_with_pre(SCL_V2, "pusp"))

        version = self.create_version(registered, "no-collection")
        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(
                self.user, xml_adapter, get_xml_collections(xml_adapter.xml_with_pre)
            )

        registered.refresh_from_db()
        self.assertEqual(registered.collections.count(), 2)
        # coleção desconhecida: sem versão por coleção, mas current_version
        # (legado) não fica vazio
        self.assertFalse(registered.collection_pids_v2.exists())
        self.assertEqual(registered.current_version, version)
        self.assertEqual(registered.v2, SCL_V2)

    def test_add_collections_identifies_xml_collection_by_journal_pid(self):
        # Core: XML sem a coleção de origem, de periódico de mais de uma
        # coleção (ver get_xml_collection_acron)
        registered = self.create_pid_provider_xml(None)
        xml_adapter = MagicMock(xml_with_pre=make_xml_with_pre(PSI_V2, "psicousp"))
        version = self.create_version(registered, "psi")

        with patch.object(XMLVersion, "get_or_create", return_value=version):
            registered.add_collections(
                self.user, xml_adapter, get_xml_collections(xml_adapter.xml_with_pre)
            )

        registered.refresh_from_db()
        self.assertEqual(registered.collection_pids_v2_data, [PSI_DATA])
        self.assertEqual(registered.current_version, version)
        self.assertEqual(registered.v2, PSI_V2)

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

    def test_check_registered_pids_changed_registers_pid_v2_and_version_of_the_collection(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.current_version = self.create_version(registered, "scl")
        registered.save()
        psi_version = self.create_version(registered, "psi")
        self.create_collection_pid_v2(registered, self.psi, PSI_V2, psi_version)
        xml_with_pre = make_xml_with_pre(
            "S1678-51772009000300099", collection="psi"
        )

        changed = registered.check_registered_pids_changed(xml_with_pre)

        pid_v2_changes = [item for item in changed if item["pid_type"] == "pid_v2"]
        self.assertEqual(len(pid_v2_changes), 1)
        self.assertEqual(pid_v2_changes[0]["registered"], PSI_V2)
        self.assertEqual(pid_v2_changes[0]["version"], psi_version)


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


class CollectionVersionTestBase(MultiCollectionJournalTestBase):
    def create_collection_version(self, registered, finger_print, collection, pid_v2):
        version = self.create_version(registered, finger_print)
        self.create_collection_pid_v2(registered, collection, pid_v2, version)
        return version


class ReasonsToUpdateTest(CollectionVersionTestBase):
    """
    XML idêntico ao registrado é registrado novamente se os dados por
    coleção estão incompletos ou divergentes (ex.: documentos registrados
    antes de CollectionPidV2)
    """

    def reasons(self, registered, xml_with_pre):
        return registered.get_reasons_to_update(
            xml_with_pre, get_xml_collections(xml_with_pre)
        )

    def create_complete(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.collections.add(self.scl, self.psi)
        scl_version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2
        )
        self.create_collection_version(registered, "psi", self.psi, PSI_V2)
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

    def test_journal_in_more_collections_than_collection_pids_v2(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.collections.add(self.scl, self.psi)
        version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2
        )
        registered.current_version = version
        registered.save()

        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
            ["missing_collection_pids_v2"],
        )

    def test_collection_pid_v2_without_version_is_missing(self):
        registered = self.create_complete()
        registered.collection_pids_v2.filter(collection=self.psi).update(
            current_version=None
        )
        self.assertIn(
            "missing_collection_pids_v2",
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
        )

    def test_missing_journal_collections(self):
        registered = self.create_complete()
        registered.collections.remove(self.psi)
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
            ["missing_journal_collections"],
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

    def test_main_collection_xml_and_legacy_fields_of_another_collection(self):
        # ex.: legado da instância do Brasil com os dados de psi
        registered = self.create_complete()
        registered.v2 = PSI_V2
        registered.current_version = registered.get_current_version(self.psi)
        registered.save()

        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")),
            ["main_collection_data_differs"],
        )
        # XML de outra coleção não exige os dados da coleção principal
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(PSI_V2, "psicousp", collection="psi")),
            [],
        )

    def test_empty_legacy_fields(self):
        registered = self.create_complete()
        PidProviderXML.objects.filter(pk=registered.pk).update(
            v2=None, current_version=None
        )
        registered.refresh_from_db()
        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(PSI_V2, "psicousp", collection="psi")),
            ["missing_v2", "missing_current_version"],
        )

    def test_xml_without_collection_is_identified_by_journal_pid(self):
        # Core: ver get_xml_collection_acron
        registered = self.create_complete()
        registered.v2 = PSI_V2
        registered.current_version = registered.get_current_version(self.psi)
        registered.save()

        self.assertEqual(
            self.reasons(registered, make_xml_with_pre(SCL_V2, "pusp")),
            ["main_collection_data_differs"],
        )

    def test_unregistered_or_without_journal_collections(self):
        xml_with_pre = make_xml_with_pre(SCL_V2, "pusp", collection="scl")
        self.assertEqual(
            PidProviderXML().get_reasons_to_update(
                xml_with_pre, get_xml_collections(xml_with_pre)
            ),
            [],
        )
        self.assertEqual(
            self.create_complete().get_reasons_to_update(xml_with_pre, []), []
        )


class IsUpdatedWithCollectionsTest(CollectionVersionTestBase):
    def is_updated(self, registered, xml_with_pre):
        return PidProviderXML.is_updated(
            xml_with_pre,
            registered,
            force_update=False,
            origin_date=None,
            registered_in_core=None,
            xml_collections=get_xml_collections(xml_with_pre),
        )

    def create_registered(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.collections.add(self.scl, self.psi)
        version = self.create_collection_version(registered, "scl", self.scl, SCL_V2)
        registered.current_version = version
        registered.readable_data = {"x": 1}
        registered.save()
        return registered

    @patch.object(XMLVersion, "is_equal_to", return_value=True)
    def test_equal_xml_with_incomplete_collection_data_is_updated(self, is_equal):
        registered = self.create_registered()
        # psi não registrada: não ignora o XML idêntico de scl
        self.assertIsNone(
            self.is_updated(registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl"))
        )

        self.create_collection_version(registered, "psi", self.psi, PSI_V2)
        with self.assertRaises(exceptions.SkipSavePidProviderXML):
            self.is_updated(
                registered, make_xml_with_pre(SCL_V2, "pusp", collection="scl")
            )

    @patch.object(XMLVersion, "is_equal_to", return_value=True)
    def test_equal_xml_without_collection_of_single_collection_journal(self, is_equal):
        SciELOJournal.objects.filter(collection=self.psi).delete()
        registered = self.create_pid_provider_xml(SCL_V2)
        registered.collections.add(self.scl)
        registered.current_version = self.create_collection_version(
            registered, "scl", self.scl, SCL_V2
        )
        registered.readable_data = {"x": 1}
        registered.save()

        # XML sem a coleção de origem é da única coleção do periódico
        with self.assertRaises(exceptions.SkipSavePidProviderXML):
            self.is_updated(registered, make_xml_with_pre(SCL_V2, "pusp"))


class GetPidV2Test(CollectionVersionTestBase):
    """pid v2 do documento na coleção (ver complete_missing_xml_pids)"""

    def test_pid_v2_of_the_collection(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        self.create_collection_version(registered, "scl", self.scl, SCL_V2)
        self.create_collection_version(registered, "psi", self.psi, PSI_V2)

        self.assertEqual(registered.get_pid_v2(), SCL_V2)
        self.assertEqual(registered.get_pid_v2("scl"), SCL_V2)
        self.assertEqual(registered.get_pid_v2("psi"), PSI_V2)

    def test_pid_v2_of_other_collection_is_not_returned(self):
        registered = self.create_pid_provider_xml(SCL_V2)
        self.create_collection_version(registered, "scl", self.scl, SCL_V2)

        self.assertIsNone(registered.get_pid_v2("psi"))

    def test_legacy_pid_v2(self):
        # documento registrado antes de CollectionPidV2
        registered = self.create_pid_provider_xml(SCL_V2)
        self.assertEqual(registered.get_pid_v2("psi"), SCL_V2)
        self.assertEqual(PidProviderXML(v2=SCL_V2).get_pid_v2("psi"), SCL_V2)
