import logging
import unittest
from unittest.mock import MagicMock, patch

from article.tasks import task_create_article_visual_counts

MODULE_PATH = "article.tasks"


def setUpModule():
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


def make_user(user_id=1, username="counts-user"):
    return MagicMock(id=user_id, username=username)


class TestTaskCreateArticleVisualCounts(unittest.TestCase):
    def test_fills_counts_for_articles_with_xml_without_load_article(self):
        user = make_user()
        first = MagicMock(id=10)
        second = MagicMock(id=11)
        qs = MagicMock()
        qs.iterator.return_value = iter([first, second])

        with patch(f"{MODULE_PATH}._get_user", return_value=user), patch(
            f"{MODULE_PATH}.Article"
        ) as MockArticle, patch(f"{MODULE_PATH}.load_article") as mock_load_article:
            MockArticle.objects.filter.return_value = qs
            task_create_article_visual_counts()

        MockArticle.objects.filter.assert_called_once_with(pp_xml__isnull=False)
        first.create_or_update_article_visual_counts.assert_called_once_with(user)
        second.create_or_update_article_visual_counts.assert_called_once_with(user)
        mock_load_article.assert_not_called()

    def test_article_error_is_logged_and_iteration_continues(self):
        user = make_user()
        failing = MagicMock(id=10)
        failing.create_or_update_article_visual_counts.side_effect = ValueError("no xml")
        following = MagicMock(id=11)
        qs = MagicMock()
        qs.iterator.return_value = iter([failing, following])

        with patch(f"{MODULE_PATH}._get_user", return_value=user), patch(
            f"{MODULE_PATH}.Article"
        ) as MockArticle, patch(f"{MODULE_PATH}.UnexpectedEvent") as mock_event:
            MockArticle.objects.filter.return_value = qs
            task_create_article_visual_counts()

        mock_event.create.assert_called_once()
        following.create_or_update_article_visual_counts.assert_called_once_with(user)

    def test_article_id_restricts_the_queryset(self):
        user = make_user()
        qs = MagicMock()
        qs.filter.return_value = qs
        qs.iterator.return_value = iter([])

        with patch(f"{MODULE_PATH}._get_user", return_value=user), patch(
            f"{MODULE_PATH}.Article"
        ) as MockArticle:
            MockArticle.objects.filter.return_value = qs
            task_create_article_visual_counts(article_id=10)

        MockArticle.objects.filter.assert_called_once_with(pp_xml__isnull=False)
        qs.filter.assert_called_once_with(pk=10)
