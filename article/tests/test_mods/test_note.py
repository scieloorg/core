import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from article.models import Article
from article.search_indexes import ArticleOAIMODSIndex

User = get_user_model()


class MODSNoteTestCase(TestCase):
    """
    Testes unitários mínimos para elemento note MODS
    Atualmente retorna vazio - reservado para uso futuro
    """

    @classmethod
    def setUpTestData(cls):
        """Dados compartilhados entre testes"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )

    def setUp(self):
        """Configuração por teste"""
        self.index = ArticleOAIMODSIndex()

    def _create_test_article(self, **kwargs):
        """Helper para criar artigo"""
        defaults = {
            'sps_pkg_name': f'test-{uuid.uuid4().hex[:12]}',
            'pid_v3': f'test-{uuid.uuid4().hex[:12]}',
            'creator': self.user
        }
        defaults.update(kwargs)
        return Article.objects.create(**defaults)

    def test_note_returns_empty_list(self):
        """Teste: note retorna lista vazia"""
        article = self._create_test_article()

        notes = self.index.prepare_mods_note(article)

        self.assertIsInstance(notes, list)
        self.assertEqual(len(notes), 0)

    def test_note_consistency(self):
        """Teste: consistência do retorno"""
        article = self._create_test_article()

        result1 = self.index.prepare_mods_note(article)
        result2 = self.index.prepare_mods_note(article)

        self.assertEqual(result1, result2)
        self.assertEqual(result1, [])


# Comando para executar os testes:
# python manage.py test --keepdb article.tests.test_mods.test_note.MODSNoteTestCase --parallel 2 -v 2
