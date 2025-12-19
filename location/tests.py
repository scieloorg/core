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


class CityStatusTest(TestCase):
    def test_city_default_status_is_raw(self):
        """Test that City objects have RAW status by default"""
        user, created = User.objects.get_or_create(username="adm")
        city = models.City.create(user=user, name="Test City")
        self.assertEqual(city.status, "RAW")

    def test_city_status_can_be_set(self):
        """Test that City status can be set to different values"""
        user, created = User.objects.get_or_create(username="adm")
        city = models.City.create(user=user, name="Verified City", status="VERIFIED")
        self.assertEqual(city.status, "VERIFIED")

    def test_city_clean_data_removes_html(self):
        """Test that clean_data removes HTML tags"""
        dirty_name = "<p>City Name</p>"
        cleaned = models.City.clean_data(dirty_name)
        self.assertEqual(cleaned, "City Name")

    def test_city_clean_data_removes_extra_spaces(self):
        """Test that clean_data removes extra spaces"""
        dirty_name = "City   Name   with   spaces"
        cleaned = models.City.clean_data(dirty_name)
        self.assertEqual(cleaned, "City Name with spaces")

    def test_city_clean_data_handles_none(self):
        """Test that clean_data handles None values"""
        cleaned = models.City.clean_data(None)
        self.assertIsNone(cleaned)


class StateStatusTest(TestCase):
    def test_state_default_status_is_raw(self):
        """Test that State objects have RAW status by default"""
        user, created = User.objects.get_or_create(username="adm")
        state = models.State.create(user=user, name="Test State", acronym="TS")
        self.assertEqual(state.status, "RAW")

    def test_state_status_can_be_set(self):
        """Test that State status can be set to different values"""
        user, created = User.objects.get_or_create(username="adm")
        state = models.State.create(user=user, name="Verified State", acronym="VS", status="VERIFIED")
        self.assertEqual(state.status, "VERIFIED")

    def test_state_clean_data_removes_html(self):
        """Test that clean_data removes HTML tags from name and acronym"""
        dirty_name = "<b>State Name</b>"
        dirty_acronym = "<i>ST</i>"
        cleaned_name, cleaned_acronym = models.State.clean_data(dirty_name, dirty_acronym)
        self.assertEqual(cleaned_name, "State Name")
        self.assertEqual(cleaned_acronym, "ST")

    def test_state_clean_data_removes_extra_spaces(self):
        """Test that clean_data removes extra spaces"""
        dirty_name = "State   Name"
        dirty_acronym = "SP "
        cleaned_name, cleaned_acronym = models.State.clean_data(dirty_name, dirty_acronym)
        self.assertEqual(cleaned_name, "State Name")
        self.assertEqual(cleaned_acronym, "SP")

    def test_state_clean_data_handles_none(self):
        """Test that clean_data handles None values"""
        cleaned_name, cleaned_acronym = models.State.clean_data(None, None)
        self.assertIsNone(cleaned_name)
        self.assertIsNone(cleaned_acronym)


class CountryStatusTest(TestCase):
    def test_country_default_status_is_raw(self):
        """Test that Country objects have RAW status by default"""
        user, created = User.objects.get_or_create(username="adm")
        country = models.Country.create_or_update(
            user=user, name="Test Country", acronym="TC"
        )
        self.assertEqual(country.status, "RAW")

    def test_country_status_can_be_set(self):
        """Test that Country status can be set to different values"""
        user, created = User.objects.get_or_create(username="adm")
        country = models.Country.create_or_update(
            user=user, name="Verified Country", acronym="VC", status="VERIFIED"
        )
        self.assertEqual(country.status, "VERIFIED")

    def test_country_clean_data_removes_html(self):
        """Test that clean_data removes HTML tags"""
        dirty_name = "<strong>Country Name</strong>"
        dirty_acronym = "<em>CN</em>"
        dirty_acron3 = "<span>CNT</span>"
        cleaned_name, cleaned_acronym, cleaned_acron3 = models.Country.clean_data(
            dirty_name, dirty_acronym, dirty_acron3
        )
        self.assertEqual(cleaned_name, "Country Name")
        self.assertEqual(cleaned_acronym, "CN")
        self.assertEqual(cleaned_acron3, "CNT")

    def test_country_clean_data_removes_extra_spaces(self):
        """Test that clean_data removes extra spaces"""
        dirty_name = "Country   Name"
        dirty_acronym = "CN "
        dirty_acron3 = "CNT "
        cleaned_name, cleaned_acronym, cleaned_acron3 = models.Country.clean_data(
            dirty_name, dirty_acronym, dirty_acron3
        )
        self.assertEqual(cleaned_name, "Country Name")
        self.assertEqual(cleaned_acronym, "CN")
        self.assertEqual(cleaned_acron3, "CNT")

    def test_country_clean_data_handles_none(self):
        """Test that clean_data handles None values"""
        cleaned_name, cleaned_acronym, cleaned_acron3 = models.Country.clean_data(
            None, None, None
        )
        self.assertIsNone(cleaned_name)
        self.assertIsNone(cleaned_acronym)
        self.assertIsNone(cleaned_acron3)
