"""
Testes de unidade de CollectionPidV2 (pid v2 e versão do XML do documento
em cada coleção) e da verificação de mudança de pid v2 por coleção.

A base dos testes e os demais cenários multicoleção estão em
test_multi_collection.py; os cenários de registro com XML real, em
test_register_multi_collection.py
"""

from unittest.mock import patch

from pid_provider.models import CollectionPidV2, XMLVersion
from pid_provider.tests.test_multi_collection import (
    ISSN_ELECTRONIC,
    PSI_V2,
    SCL_V2,
    MultiCollectionJournalTestBase,
    make_xml_with_pre,
)


class CollectionPidV2TestBase(MultiCollectionJournalTestBase):
    def create_collection_pid_v2(self, registered, collection, pid_v2, version):
        return CollectionPidV2.create_or_update(
            self.user,
            pid_provider_xml=registered,
            collection=collection,
            pid_v2=pid_v2,
            journal_acron="pusp" if collection == self.scl else "psicousp",
            current_version=version,
        )


class CollectionPidV2Test(CollectionPidV2TestBase):
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
            if name == "journal_acron":
                continue
            with self.subTest(missing=name):
                with self.assertRaises(ValueError):
                    CollectionPidV2.create_or_update(**{**params, name: None})
        self.assertFalse(CollectionPidV2.objects.exists())

    def test_create_or_update_without_journal_acron(self):
        # journal_acron é o do XML, que pode não o informar
        registered = self.create_pid_provider_xml()
        version = self.create_version(registered, "v1")
        obj = CollectionPidV2.create_or_update(
            self.user, registered, self.psi, PSI_V2, None, version
        )
        self.assertIsNone(obj.journal_acron)
        self.assertEqual(obj.current_version, version)

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
        registered.current_version = self.create_version(registered, "previous")
        registered.save()

        # nenhuma versão por coleção: usa PidProviderXML.current_version
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


class CheckRegisteredPidsChangedByCollectionTest(CollectionPidV2TestBase):
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
