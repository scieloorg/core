from django.test import SimpleTestCase

from collection.models import normalize_network_classification


class NormalizeNetworkClassificationTest(SimpleTestCase):
    def test_str_becomes_list(self):
        self.assertEqual(
            normalize_network_classification("scielonetwork"), ["scielonetwork"]
        )

    def test_list_is_kept(self):
        self.assertEqual(
            normalize_network_classification(["scielonetwork", "thematic"]),
            ["scielonetwork", "thematic"],
        )

    def test_tuple_becomes_list(self):
        self.assertEqual(normalize_network_classification(("thematic",)), ["thematic"])

    def test_empty_values_become_none(self):
        for value in (None, "", [], (), [""], [None]):
            with self.subTest(value=value):
                self.assertIsNone(normalize_network_classification(value))

    def test_empty_items_are_removed(self):
        self.assertEqual(
            normalize_network_classification(["", "thematic", None]), ["thematic"]
        )
