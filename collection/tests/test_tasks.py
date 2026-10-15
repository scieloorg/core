from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from collection import tasks

User = get_user_model()


@patch("collection.tasks.Collection.complete_network_classification")
class TaskCompleteNetworkClassificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="tester")

    def test_runs_with_username(self, mock_complete):
        mock_complete.return_value = {"updated": ["scl"], "not_found": []}

        result = tasks.task_complete_network_classification(username="tester")

        mock_complete.assert_called_once_with(self.user)
        self.assertEqual(result, {"updated": ["scl"], "not_found": []})

    def test_runs_with_user_id(self, mock_complete):
        tasks.task_complete_network_classification(user_id=self.user.pk)

        mock_complete.assert_called_once_with(self.user)

    def test_requires_user(self, mock_complete):
        with self.assertRaises(ValueError):
            tasks.task_complete_network_classification()

        mock_complete.assert_not_called()
