from django.contrib.auth import get_user_model
from django.test import TestCase

from collection.models import Collection
from collection.wagtail_hooks import CollectionFilterSet

User = get_user_model()


class CollectionFilterSetTest(TestCase):
    def setUp(self):
        user = User.objects.create(username="tester")
        Collection.objects.create(
            acron3="scl", network_classification=["scielonetwork"], creator=user
        )
        Collection.objects.create(
            acron3="spa",
            network_classification=["scielonetwork", "thematic"],
            creator=user,
        )
        Collection.objects.create(
            acron3="psi", network_classification=["thematic"], creator=user
        )
        Collection.objects.create(acron3="xyz", creator=user)

    def filter_acronyms(self, data):
        filterset = CollectionFilterSet(data, queryset=Collection.objects.all())
        self.assertTrue(filterset.is_valid(), filterset.errors)
        return sorted(filterset.qs.values_list("acron3", flat=True))

    def test_without_filter_returns_all(self):
        self.assertEqual(self.filter_acronyms({}), ["psi", "scl", "spa", "xyz"])

    def test_filter_by_one_network_classification(self):
        self.assertEqual(
            self.filter_acronyms({"network_classification": ["thematic"]}),
            ["psi", "spa"],
        )

    def test_filter_by_any_of_network_classifications(self):
        self.assertEqual(
            self.filter_acronyms(
                {"network_classification": ["scielonetwork", "thematic"]}
            ),
            ["psi", "scl", "spa"],
        )

    def test_invalid_choice_is_rejected(self):
        filterset = CollectionFilterSet(
            {"network_classification": ["unknown"]},
            queryset=Collection.objects.all(),
        )
        self.assertFalse(filterset.is_valid())
