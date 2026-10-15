from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from collection.models import ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY, Collection

User = get_user_model()


@override_settings(COLLECTION_ENSURE_NETWORK_CLASSIFICATION=True)
class EnsureNetworkClassificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="tester")
        cache.delete(ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY)
        self.addCleanup(cache.delete, ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY)
        patcher = patch(
            "collection.models.fetch_data",
            return_value=[
                {"acron": "scl", "network_classification": ["scielonetwork"]},
            ],
        )
        self.mock_fetch_data = patcher.start()
        self.addCleanup(patcher.stop)

    def test_completes_collections_without_network_classification(self):
        Collection.objects.create(acron3="scl", creator=self.user)

        result = Collection.ensure_network_classification(self.user)

        self.assertEqual(result, {"updated": ["scl"], "not_found": []})
        self.assertTrue(
            Collection.objects.get(acron3="scl").is_national_journal_collection
        )
        self.mock_fetch_data.assert_called_once()

    def test_does_not_fetch_when_all_collections_are_complete(self):
        Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=self.user
        )

        self.assertIsNone(Collection.ensure_network_classification(self.user))
        self.mock_fetch_data.assert_not_called()

    def test_fetches_at_most_once_per_interval(self):
        # coleção ausente no articlemeta continua sem network_classification
        Collection.objects.create(acron3="xyz", creator=self.user)

        result = Collection.ensure_network_classification(self.user)
        self.assertEqual(result, {"updated": [], "not_found": ["xyz"]})
        self.assertIsNone(Collection.ensure_network_classification(self.user))
        self.mock_fetch_data.assert_called_once()

        # após o intervalo, consulta novamente
        cache.delete(ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY)
        Collection.ensure_network_classification(self.user)
        self.assertEqual(self.mock_fetch_data.call_count, 2)

    def test_does_not_raise_when_articlemeta_fails(self):
        self.mock_fetch_data.side_effect = Exception("articlemeta indisponível")
        Collection.objects.create(acron3="scl", creator=self.user)

        self.assertIsNone(Collection.ensure_network_classification(self.user))
        self.assertIsNone(Collection.objects.get(acron3="scl").network_classification)

    @override_settings(COLLECTION_ENSURE_NETWORK_CLASSIFICATION=False)
    def test_does_nothing_when_disabled(self):
        Collection.objects.create(acron3="scl", creator=self.user)

        self.assertIsNone(Collection.ensure_network_classification(self.user))
        self.mock_fetch_data.assert_not_called()
        self.assertIsNone(Collection.objects.get(acron3="scl").network_classification)
