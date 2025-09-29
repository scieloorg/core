import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex
from collection.models import Collection
from core.models import Language
from journal.models import Journal, OfficialJournal, SciELOJournal

User = get_user_model()


class MODSRecordInfoTestCase(TestCase):
    """
    Testes unitários mínimos para elemento recordInfo MODS
    Testa metadados sobre o registro de catalogação
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes para melhor performance"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

        # Criar idiomas
        cls.lang_pt = Language.objects.create(
            code2='pt',
            name='Português',
            creator=cls.user
        )

        cls.lang_en = Language.objects.create(
            code2='en',
            name='English',
            creator=cls.user
        )

        # Criar coleção
        cls.collection = Collection.objects.create(
            acron3='scl',
            main_name='SciELO Brasil',
            creator=cls.user
        )

    def setUp(self):
        """Configuração mínima por teste"""
        self.index = ArticleOAIMODSIndex()

    def _create_test_article(self, **kwargs):
        """Helper otimizado para criar artigo de teste"""
        defaults = {
            'sps_pkg_name': f'test-{uuid.uuid4().hex[:12]}',
            'pid_v3': f'test-{uuid.uuid4().hex[:12]}',
            'article_type': 'research-article',
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def _create_test_journal(self):
        """Helper para criar journal com coleção"""
        official = OfficialJournal.objects.create(
            title='Test Journal',
            issn_print='0102-311X',
            creator=self.user
        )

        journal = Journal.objects.create(
            official=official,
            title='Test Journal',
            creator=self.user
        )

        SciELOJournal.objects.create(
            journal=journal,
            collection=self.collection,
            journal_acron='test',
            creator=self.user
        )

        return journal

    def test_record_info_basic_structure(self):
        """Teste: estrutura básica do recordInfo"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)

        self.assertIsInstance(record_info, list)
        self.assertEqual(len(record_info), 1)
        self.assertIsInstance(record_info[0], dict)

    def test_record_content_source_with_collection(self):
        """Teste: recordContentSource com coleção"""
        journal = self._create_test_journal()
        article = self._create_test_article(journal=journal)

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('recordContentSource', record_data)
        self.assertEqual(record_data['recordContentSource'], 'SciELO Brasil')

    def test_record_content_source_without_journal(self):
        """Teste: recordContentSource fallback sem journal"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('recordContentSource', record_data)
        self.assertEqual(record_data['recordContentSource'], 'SciELO')

    def test_record_creation_date_structure(self):
        """Teste: estrutura do recordCreationDate"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('recordCreationDate', record_data)
        creation_date = record_data['recordCreationDate']

        self.assertIsInstance(creation_date, dict)
        self.assertEqual(creation_date['encoding'], 'w3cdtf')
        self.assertIn('text', creation_date)
        self.assertRegex(creation_date['text'], r'^\d{4}-\d{2}-\d{2}$')

    def test_record_change_date_structure(self):
        """Teste: estrutura do recordChangeDate"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('recordChangeDate', record_data)
        change_date = record_data['recordChangeDate']

        self.assertIsInstance(change_date, dict)
        self.assertEqual(change_date['encoding'], 'w3cdtf')
        self.assertIn('text', change_date)
        self.assertRegex(change_date['text'], r'^\d{4}-\d{2}-\d{2}$')

    def test_record_identifier_with_pid_v3(self):
        """Teste: recordIdentifier com pid_v3"""
        pid_v3 = 'ABC123XYZ'
        article = self._create_test_article(pid_v3=pid_v3)

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('recordIdentifier', record_data)
        identifier = record_data['recordIdentifier']

        self.assertIsInstance(identifier, dict)
        self.assertEqual(identifier['source'], 'SciELO')
        self.assertEqual(identifier['text'], pid_v3)

    def test_record_identifier_fallback_to_pid_v2(self):
        """Teste: recordIdentifier fallback para pid_v2"""
        pid_v2 = 'S0102-311X2024000100001'
        article = self._create_test_article(pid_v3=None, pid_v2=pid_v2)

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        identifier = record_data['recordIdentifier']
        self.assertEqual(identifier['text'], pid_v2)

    def test_record_origin(self):
        """Teste: recordOrigin fixo"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('recordOrigin', record_data)
        self.assertEqual(record_data['recordOrigin'], 'Generated from SciELO SPS XML')

    def test_description_standard(self):
        """Teste: descriptionStandard fixo"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('descriptionStandard', record_data)
        self.assertEqual(record_data['descriptionStandard'], 'SciELO SPS')

    def test_language_of_cataloging_with_article_language(self):
        """Teste: languageOfCataloging com idioma do artigo"""
        article = self._create_test_article()
        article.languages.add(self.lang_en)

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        self.assertIn('languageOfCataloging', record_data)
        lang_cataloging = record_data['languageOfCataloging']

        self.assertIsInstance(lang_cataloging, dict)
        self.assertIn('languageTerm', lang_cataloging)

        lang_term = lang_cataloging['languageTerm']
        self.assertEqual(lang_term['type'], 'code')
        self.assertEqual(lang_term['authority'], 'iso639-2b')
        self.assertEqual(lang_term['text'], 'eng')

    def test_language_of_cataloging_fallback(self):
        """Teste: languageOfCataloging fallback para português"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        lang_cataloging = record_data['languageOfCataloging']
        lang_term = lang_cataloging['languageTerm']
        self.assertEqual(lang_term['text'], 'por')

    def test_complete_structure(self):
        """Teste: estrutura completa com todos os elementos"""
        journal = self._create_test_journal()
        article = self._create_test_article(
            journal=journal,
            pid_v3='COMPLETE123'
        )
        article.languages.add(self.lang_pt)

        record_info = self.index.prepare_mods_record_info(article)
        record_data = record_info[0]

        # Verificar todos os campos obrigatórios
        required_fields = [
            'recordContentSource',
            'recordCreationDate',
            'recordChangeDate',
            'recordIdentifier',
            'recordOrigin',
            'descriptionStandard',
            'languageOfCataloging'
        ]

        for field in required_fields:
            self.assertIn(field, record_data, f"Campo {field} não encontrado")

    def test_return_type_consistency(self):
        """Teste: consistência do tipo de retorno"""
        article = self._create_test_article()

        record_info = self.index.prepare_mods_record_info(article)

        self.assertIsInstance(record_info, list)
        self.assertEqual(len(record_info), 1)
        self.assertIsInstance(record_info[0], dict)

# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_record_info.MODSRecordInfoTestCase --parallel 2 -v 2
