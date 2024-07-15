from django.test import SimpleTestCase

# Create your tests here.
from researcher.models import PersonName


class PersonNameJoinNameTest(SimpleTestCase):
    def test_person_name_join_name(self):
        test_cases = [
            (['Palavra1', None, None], 'Palavra1'),
            (['Palavra1', 'Palavra2', None], 'Palavra1 Palavra2' ),
            (['Palavra1', 'Palavra2', 'Palavra3'], 'Palavra1 Palavra2 Palavra3'),
        ]

        for text, expected in test_cases:
            with self.subTest(text=text, excepted=expected):
                result = PersonName.join_names(*text)
                self.assertEqual(expected, result)