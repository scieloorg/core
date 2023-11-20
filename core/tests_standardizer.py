from django.test import TestCase

# Create your tests here.
from core.utils import standardizer


# def get_separators(text, exclusion_list=None):
# def get_splitted_text(text):
# def standardize_acronym_and_name(original, possible_multiple_return=None, q_locations=None):
# def standardize_acronym_and_name_one(splitted_text, acrons, names):
# def standardize_acronym_and_name_multiple(q_locations, splitted_text, acrons, names):
# def name_and_divisions(splitted_text):
# def standardize_code_and_name(original):
# def standardize_name(original):


class StandardizerGetSeparatorsTest(TestCase):
    def test_get_separators_returns_empty_list(self):
        expected = []
        text = "ABC abc"
        result = standardizer.get_separators(text, exclusion_list=None)
        self.assertEqual(expected, result)

    def test_get_separators_returns_list(self):
        expected = [",", '/', '-', ';', '(', ')']
        text = "ABC, abc / X - Y; (C)"
        result = standardizer.get_separators(text, exclusion_list=None)
        self.assertEqual(expected, result)


class StandardizerGetSplittedTextTest(TestCase):

    def test_get_splitted_text(self):
        expected = ["ABC", "abc", "X", "Y", "C"]
        text = "ABC, abc / X - Y; (C)"
        result = standardizer.get_splitted_text(text)
        self.assertEqual(expected, result)


class StandardizerStandardizeAcronymAndNameTest(TestCase):

    def test_standardize_acronym_and_name(self):
        expected = [{"acronym": "ABC", "name": "Abc"}]
        text = "ABC / Abc"
        result = standardizer.standardize_acronym_and_name(
            text, possible_multiple_return=None, q_locations=None)
        self.assertEqual(expected, list(result))

    def test_standardize_acronym_and_name_returns_levels(self):
        expected = [{
            "acronym": "ABC", "name": "Abc",
            "level_1": "Faculdade FFF",
            "level_2": "Unidade UUUU",
            "level_3": "Programa XXXX",
        }]
        text = "ABC / Abc - Faculdade FFF - Unidade UUUU - Programa XXXX"
        result = standardizer.standardize_acronym_and_name(
            text, possible_multiple_return=None, q_locations=None)

        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertEqual(expected[i], item)


class StandardizerStandardizeAcronymAndNameOneTest(TestCase):

    def test_standardize_acronym_and_name_one(self):
        expected = {
            "acronym": "ABC", "name": "Abc",
            "level_1": "Faculdade FFF",
            "level_2": "Unidade UUUU",
            "level_3": "Programa XXXX",
        }
        acrons = ["ABC"]
        names = ["Abc", "Faculdade FFF", "Unidade UUUU", "Programa XXXX", ]
        splitted_text = ["ABC", "Abc", "Faculdade FFF", "Unidade UUUU", "Programa XXXX", ]
        result = standardizer.standardize_acronym_and_name_one(
            splitted_text, acrons, names)
        self.assertDictEqual(expected, result)


class StandardizerStandardizeAcronymAndNameMultTest(TestCase):

    def test_standardize_acronym_and_name_multiple(self):
        expected = [
            {"acronym": "ABC", "name": "Abc"},
            {"name": "Faculdade FFF"},
            {"name": "Unidade UUUU"},
            {"name": "Programa XXXX"},
        ]
        splitted_text = ["ABC", "Abc", "Faculdade FFF", "Unidade UUUU", "Programa XXXX", ]
        q_locations = None
        original = "ABC / Abc - Faculdade FFF - Unidade UUUU - Programa XXXX"
        acrons = ["ABC"]
        names = ["Abc", "Faculdade FFF", "Unidade UUUU", "Programa XXXX", ]
        result = standardizer.standardize_acronym_and_name_multiple(
            splitted_text, acrons, names, original, q_locations,
        )
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertDictEqual(expected[i], item)


class StandardizerNameAndDivisionsTest(TestCase):

    def test_name_and_divisions(self):
        expected = {
            "name": "Abc",
            "level_1": "Faculdade FFF",
            "level_2": "Unidade UUUU",
            "level_3": "Programa XXXX",
        }
        splitted_text = ["Abc", "Faculdade FFF", "Unidade UUUU", "Programa XXXX", ]
        result = standardizer.name_and_divisions(splitted_text)
        self.assertEqual(expected, result)


class StandardizerStandardizeCodeAndNameTest(TestCase):

    def test_standardize_code_and_name_returns_both(self):
        expected = [{"code": "CE", "name": "Ceará"}]
        text = "Ceará / CE"
        result = standardizer.standardize_code_and_name(text)
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertDictEqual(expected[i], item)

    def test_standardize_code_and_name_returns_acronym(self):
        expected = [{"code": "CE", }]
        text = "CE"
        result = standardizer.standardize_code_and_name(text)
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertDictEqual(expected[i], item)

    def test_standardize_code_and_name_returns_name(self):
        expected = [{"name": "Ceará"}]
        text = "Ceará"
        result = standardizer.standardize_code_and_name(text)
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertDictEqual(expected[i], item)

    def test_standardize_code_and_name_returns_more_than_one_both(self):
        expected = [{"code": "CE", "name": "Ceará"},
            {"code": "SP", "name": "São Paulo"}]
        text = "Ceará / CE, São Paulo / SP"
        result = standardizer.standardize_code_and_name(text)
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertDictEqual(expected[i], item)

    def test_standardize_code_and_name_returns_more_than_one_acronym(self):
        expected = [{"code": "CE", }, {"code": "SP", }]
        text = "CE / SP"
        result = standardizer.standardize_code_and_name(text)
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertDictEqual(expected[i], item)

    def test_standardize_code_and_name_returns_more_than_one_name(self):
        expected = [{"name": "Ceará"}, {"name": "São Paulo"}]
        text = "Ceará - São Paulo"
        result = standardizer.standardize_code_and_name(text)
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertDictEqual(expected[i], item)


class StandardizerStandardizeNameTest(TestCase):

    def test_standardize_name(self):
        expected = ["Txto 1", "Texto 2", "Texto 3"]
        text = "Txto 1,    Texto 2,    Texto   3"
        result = standardizer.standardize_name(text)
        for i, item in enumerate(result):
            with self.subTest(i):
                self.assertEqual(expected[i], item)
