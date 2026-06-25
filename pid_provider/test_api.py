from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from pid_provider.api.v1.views import PublishedArticleRegistrationViewSet
from pid_provider.models import PidProviderXML


User = get_user_model()


class PublishedArticleRegistrationViewSetTest(APITestCase):
    url = "/api/v1/published_article/"
    pid_v3 = "12345678901234567890123"
    sps_pkg_name = "1234-5678-journal-10-01-a01"

    def setUp(self):
        self.user = User.objects.create_user(
            username="scms-upload",
            password="test-password",
        )
        self.factory = APIRequestFactory()
        self.view = PublishedArticleRegistrationViewSet.as_view({"post": "create"})
        self.authenticated = False
        PidProviderXML.objects.filter(
            v3=self.pid_v3,
            pkg_name=self.sps_pkg_name,
        ).delete()

    def authenticate(self):
        self.authenticated = True

    def create_pid_provider_xml(self):
        return PidProviderXML.objects.create(
            v3=self.pid_v3,
            pkg_name=self.sps_pkg_name,
        )

    def post(self, data=None, url=None):
        request = self.factory.post(
            url or self.url,
            data or {"pid_v3": self.pid_v3, "sps_pkg_name": self.sps_pkg_name},
            format="json",
        )
        if self.authenticated:
            force_authenticate(request, user=self.user)
        return self.view(request)

    def registration_result(self, operation="created"):
        return {
            "article": object(),
            "article_id": 123,
            "pid_v3": self.pid_v3,
            "sps_pkg_name": self.sps_pkg_name,
            "operation": operation,
            "data_status": "PUBLIC",
            "is_public": True,
        }

    def test_requires_authentication(self):
        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_400_when_required_params_are_missing(self):
        self.authenticate()

        response = self.post({"pid_v3": self.pid_v3})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sps_pkg_name", response.data)

    def test_returns_400_when_pid_v3_is_invalid(self):
        self.authenticate()

        response = self.post({"pid_v3": "invalid", "sps_pkg_name": self.sps_pkg_name})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pid_v3", response.data)

    def test_returns_404_when_pid_provider_xml_does_not_exist(self):
        self.authenticate()

        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "PidProviderXML not found")
        self.assertEqual(response.data["pid_v3"], self.pid_v3)
        self.assertEqual(response.data["sps_pkg_name"], self.sps_pkg_name)

    @patch(
        "pid_provider.api.v1.views.PublishedArticleRegistrationViewSet.register_published_article_from_pid_provider_xml"
    )
    def test_returns_201_when_article_is_created(self, mocked_register):
        self.authenticate()
        pp_xml = self.create_pid_provider_xml()
        mocked_register.return_value = self.registration_result(operation="created")

        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["article_id"], 123)
        self.assertEqual(response.data["pid_v3"], self.pid_v3)
        self.assertEqual(response.data["sps_pkg_name"], self.sps_pkg_name)
        self.assertEqual(response.data["operation"], "created")
        self.assertEqual(response.data["data_status"], "PUBLIC")
        self.assertTrue(response.data["is_public"])
        self.assertIn("timestamp", response.data)
        self.assertNotIn("article", response.data)
        mocked_register.assert_called_once_with(self.user, pp_xml)

    @patch(
        "pid_provider.api.v1.views.PublishedArticleRegistrationViewSet.register_published_article_from_pid_provider_xml"
    )
    def test_returns_200_when_article_is_updated(self, mocked_register):
        self.authenticate()
        pp_xml = self.create_pid_provider_xml()
        mocked_register.return_value = self.registration_result(operation="updated")

        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["article_id"], 123)
        self.assertEqual(response.data["operation"], "updated")
        mocked_register.assert_called_once_with(self.user, pp_xml)

    @patch(
        "pid_provider.api.v1.views.PublishedArticleRegistrationViewSet.register_published_article_from_pid_provider_xml"
    )
    def test_returns_400_when_registration_fails(self, mocked_register):
        self.authenticate()
        self.create_pid_provider_xml()
        mocked_register.side_effect = RuntimeError("registration failed")

        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_type"], "<class 'RuntimeError'>")
        self.assertEqual(response.data["error_message"], "registration failed")
