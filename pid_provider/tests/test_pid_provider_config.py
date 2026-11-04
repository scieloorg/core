"""Testes para PidProviderConfig (pid_provider/models.py)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from pid_provider.models import PidProviderConfig

User = get_user_model()


class PidProviderConfigGetOrCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="config-user", password="x")

    def test_creates_new_when_none_exists(self):
        obj = PidProviderConfig.get_or_create(
            creator=self.user,
            pid_provider_api_post_xml="https://example.org/post",
            pid_provider_api_get_token="https://example.org/token",
            api_username="user",
            api_password="pass",
            timeout=30,
        )

        self.assertIsNotNone(obj.pk)
        self.assertEqual(obj.pid_provider_api_post_xml, "https://example.org/post")
        self.assertEqual(obj.timeout, 30)

    def test_returns_existing_singleton_ignoring_new_arguments(self):
        """
        get_or_create usa cls.objects.first() -- se já existe QUALQUER
        registro, ele é retornado tal como está, ignorando os parâmetros
        passados na segunda chamada (não atualiza os campos).
        """
        first = PidProviderConfig.get_or_create(
            creator=self.user,
            pid_provider_api_post_xml="https://example.org/post",
        )

        second = PidProviderConfig.get_or_create(
            creator=self.user,
            pid_provider_api_post_xml="https://other.example.org/post",
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.pid_provider_api_post_xml, "https://example.org/post")
        self.assertEqual(PidProviderConfig.objects.count(), 1)

    def test_str_representation(self):
        obj = PidProviderConfig.get_or_create(
            creator=self.user, pid_provider_api_post_xml="https://example.org/post"
        )
        self.assertEqual(str(obj), "https://example.org/post")
