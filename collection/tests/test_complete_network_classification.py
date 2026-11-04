from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from collection.models import Collection

User = get_user_model()


class CompleteNetworkClassificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="tester")
        self.collections_data = [
            {"acron": "scl", "network_classification": ["scielonetwork"]},
            {"acron": "spa", "network_classification": ["scielonetwork", "thematic"]},
            {"acron": "psi", "network_classification": "thematic"},
            {"acron": "pef", "network_classification": ["independent"]},
        ]

    def test_completes_only_collections_without_network_classification(self):
        Collection.objects.create(acron3="scl", creator=self.user)
        Collection.objects.create(
            acron3="spa", network_classification=[], creator=self.user
        )
        Collection.objects.create(acron3="psi", creator=self.user)
        Collection.objects.create(
            acron3="pef", network_classification=["thematic"], creator=self.user
        )

        result = Collection.complete_network_classification(
            self.user, collections_data=self.collections_data
        )

        self.assertEqual(sorted(result["updated"]), ["psi", "scl", "spa"])
        self.assertEqual(result["not_found"], [])
        self.assertEqual(
            Collection.objects.get(acron3="scl").network_classification,
            ["scielonetwork"],
        )
        self.assertEqual(
            Collection.objects.get(acron3="spa").network_classification,
            ["scielonetwork", "thematic"],
        )
        self.assertEqual(
            Collection.objects.get(acron3="psi").network_classification,
            ["thematic"],
        )
        # já preenchida: mantém o valor atual
        self.assertEqual(
            Collection.objects.get(acron3="pef").network_classification,
            ["thematic"],
        )
        self.assertEqual(Collection.objects.get(acron3="scl").updated_by, self.user)

    def test_reports_collections_absent_from_source(self):
        Collection.objects.create(acron3="xyz", creator=self.user)

        result = Collection.complete_network_classification(
            self.user, collections_data=self.collections_data
        )

        self.assertEqual(result, {"updated": [], "not_found": ["xyz"]})
        self.assertIsNone(Collection.objects.get(acron3="xyz").network_classification)

    @patch("collection.models.fetch_data")
    def test_does_not_fetch_when_all_collections_are_complete(self, mock_fetch_data):
        Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=self.user
        )

        result = Collection.complete_network_classification(self.user)

        self.assertEqual(result, {"updated": [], "not_found": []})
        mock_fetch_data.assert_not_called()

    @patch("collection.models.fetch_data")
    def test_fetches_articlemeta_when_data_is_not_given(self, mock_fetch_data):
        mock_fetch_data.return_value = self.collections_data
        Collection.objects.create(acron3="scl", creator=self.user)

        result = Collection.complete_network_classification(self.user)

        self.assertEqual(result["updated"], ["scl"])
        mock_fetch_data.assert_called_once()
