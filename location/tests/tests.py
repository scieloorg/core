from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from location import models


User = get_user_model()


class CityTest(TestCase):
    def test_standardize_returns_city_object(self):
        text = "ABC abc"
        user, created = User.objects.get_or_create(username="adm")
        result = models.City.standardize(text, user)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["city"], models.City)
                self.assertEqual("ABC abc", item["city"].name)

    def test_standardize_returns_city_name(self):
        text = "ABC abc"
        result = models.City.standardize(text)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["city"]["name"], str)
                self.assertEqual("ABC abc", item["city"]["name"])


class StateTest(TestCase):
    def test_standardize_returns_state_object(self):
        text = "SP, São Paulo"
        user, created = User.objects.get_or_create(username="adm")
        result = models.State.standardize(text, user)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], models.State)
                self.assertEqual("São Paulo", item["state"].name)
                self.assertEqual("SP", item["state"].acronym)

    def test_standardize_returns_state_dict(self):
        text = "SP, São Paulo"
        result = models.State.standardize(text)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], dict)
                self.assertEqual("São Paulo", item["state"]["name"])
                self.assertEqual("SP", item["state"]["code"])

    def test_standardize_returns_state_object_names(self):
        text = "Minas Gerais, São Paulo"
        user, created = User.objects.get_or_create(username="adm")
        result = models.State.standardize(text, user)

        expected = ["Minas Gerais", "São Paulo"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], models.State)
                self.assertEqual(expected[i], item["state"].name)
                self.assertEqual(None, item["state"].acronym)

    def test_standardize_returns_state_dict_names(self):
        text = "Minas Gerais, São Paulo"
        result = models.State.standardize(text)

        expected = ["Minas Gerais", "São Paulo"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], dict)
                self.assertEqual(expected[i], item["state"]["name"])
                self.assertEqual(None, item["state"].get("code"))

    def test_standardize_returns_state_object_acrons(self):
        text = "SP, MG"
        user, created = User.objects.get_or_create(username="adm")
        result = models.State.standardize(text, user)

        expected = ["SP", "MG"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], models.State)
                self.assertEqual(None, item["state"].name)
                self.assertEqual(expected[i], item["state"].acronym)

    def test_standardize_returns_state_dict_acrons(self):
        text = "SP, MG"
        result = models.State.standardize(text)

        expected = ["SP", "MG"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], dict)
                self.assertEqual(None, item["state"].get("name"))
                self.assertEqual(expected[i], item["state"]["code"])

    def test_standardize_returns_object_original(self):
        text = "SP, MG, Goiás"
        user, created = User.objects.get_or_create(username="adm")
        result = models.State.standardize(text, user)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], models.State)
                self.assertEqual("SP, MG, Goiás", item["state"].name)
                self.assertEqual(None, item["state"].acronym)

    def test_standardize_returns_dict_original(self):
        text = "SP, MG, Goiás"
        result = models.State.standardize(text)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["state"], dict)
                self.assertEqual("SP, MG, Goiás", item["state"].get("name"))
                self.assertEqual(None, item["state"].get("code"))


class CountryTest(TestCase):
    def test_standardize_returns_country_object(self):
        text = "BR, Brasil"
        user, created = User.objects.get_or_create(username="adm")
        result = models.Country.standardize(text, user)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], models.Country)
                self.assertEqual("Brasil", item["country"].name)
                self.assertEqual("BR", item["country"].acronym)

    def test_standardize_returns_country_dict(self):
        text = "BR, Brasil"
        result = models.Country.standardize(text)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], dict)
                self.assertEqual("Brasil", item["country"]["name"])
                self.assertEqual("BR", item["country"]["code"])

    def test_standardize_returns_country_object_names(self):
        text = "México, Brasil"
        user, created = User.objects.get_or_create(username="adm")
        result = models.Country.standardize(text, user)

        expected = ["México", "Brasil"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], models.Country)
                self.assertEqual(expected[i], item["country"].name)
                self.assertEqual(None, item["country"].acronym)

    def test_standardize_returns_country_dict_names(self):
        text = "México, Brasil"
        result = models.Country.standardize(text)

        expected = ["México", "Brasil"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], dict)
                self.assertEqual(expected[i], item["country"]["name"])
                self.assertEqual(None, item["country"].get("code"))

    def test_standardize_returns_country_object_acrons(self):
        text = "BR, MX"
        user, created = User.objects.get_or_create(username="adm")
        result = models.Country.standardize(text, user)

        expected = ["BR", "MX"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], models.Country)
                self.assertEqual(None, item["country"].name)
                self.assertEqual(expected[i], item["country"].acronym)

    def test_standardize_returns_country_dict_acrons(self):
        text = "BR, MX"
        result = models.Country.standardize(text)

        expected = ["BR", "MX"]
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], dict)
                self.assertEqual(None, item["country"].get("name"))
                self.assertEqual(expected[i], item["country"]["code"])

    def test_standardize_returns_object_original(self):
        text = "BR, MX, Chile"
        user, created = User.objects.get_or_create(username="adm")
        result = models.Country.standardize(text, user)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], models.Country)
                self.assertEqual("BR, MX, Chile", item["country"].name)
                self.assertEqual(None, item["country"].acronym)

    def test_standardize_returns_dict_original(self):
        text = "BR, MX, Chile"
        result = models.Country.standardize(text)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertIsInstance(item["country"], dict)
                self.assertEqual("BR, MX, Chile", item["country"].get("name"))
                self.assertEqual(None, item["country"].get("code"))
