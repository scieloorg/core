import logging
import unittest
from unittest.mock import MagicMock, patch, call

# Ajuste este caminho se as tasks estiverem em outro módulo.
MODULE_PATH = "article.tasks"
from article.tasks import (  # noqa: E402
    task_harvest_articles,
    task_dispatch_articles,
    task_process_article_pipeline,
)


def setUpModule():
    """
    Desliga o logging (abaixo de CRITICAL) para todo o módulo de testes,
    evitando ruído de handlers reais (ex.: OpenSearch) configurados no
    settings.LOGGING do Django durante os testes.
    """
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


def make_user(user_id=1, username="roberta"):
    return MagicMock(id=user_id, username=username)


# =======================================================================
# task_harvest_articles
# =======================================================================
class TestTaskHarvestArticles(unittest.TestCase):
    def _patches(self):
        return (
            patch(f"{MODULE_PATH}._get_user"),
            patch(f"{MODULE_PATH}.ArticleIteratorBuilder"),
            patch(f"{MODULE_PATH}.task_process_article_pipeline"),
            patch(f"{MODULE_PATH}.UnexpectedEvent"),
        )

    def test_dispatches_pipeline_task_for_each_yielded_item(self):
        user = make_user()
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.task_process_article_pipeline") as mock_pipeline:
            mock_get_user.return_value = user
            MockBuilder.return_value.from_harvest.return_value = iter([
                {"xml_url": "http://a", "collection_acron": "scl", "pid": "S1"},
                {"xml_url": "http://b", "collection_acron": "scl", "pid": "S2"},
            ])

            task_harvest_articles(collection_acron_list=["scl"])

        self.assertEqual(mock_pipeline.delay.call_count, 2)
        first_call_kwargs = mock_pipeline.delay.call_args_list[0].kwargs
        self.assertEqual(first_call_kwargs["xml_url"], "http://a")
        self.assertEqual(first_call_kwargs["user_id"], user.id)
        self.assertEqual(first_call_kwargs["username"], user.username)

    def test_none_items_are_skipped(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.task_process_article_pipeline") as mock_pipeline:
            mock_get_user.return_value = make_user()
            MockBuilder.return_value.from_harvest.return_value = iter(
                [None, {"xml_url": "http://a"}, None]
            )

            task_harvest_articles()

        self.assertEqual(mock_pipeline.delay.call_count, 1)

    def test_builder_is_constructed_with_expected_kwargs_including_stop(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.task_process_article_pipeline"):
            user = make_user()
            mock_get_user.return_value = user
            MockBuilder.return_value.from_harvest.return_value = iter([])

            task_harvest_articles(
                collection_acron_list=["scl"],
                journal_acron_list=["abc"],
                from_date="2024-01-01",
                until_date="2024-12-31",
                force_update=True,
                limit=10,
                timeout=30,
                opac_url="www.custom.br",
                stop=5,
            )

        _, kwargs = MockBuilder.call_args
        self.assertIs(kwargs["user"], user)
        self.assertEqual(kwargs["collection_acron_list"], ["scl"])
        self.assertEqual(kwargs["journal_acron_list"], ["abc"])
        self.assertEqual(kwargs["from_date"], "2024-01-01")
        self.assertEqual(kwargs["until_date"], "2024-12-31")
        self.assertTrue(kwargs["force_update"])
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["timeout"], 30)
        self.assertEqual(kwargs["opac_url"], "www.custom.br")
        self.assertEqual(kwargs["stop"], 5)

    def test_BUG_get_user_failure_masks_original_exception_with_unboundlocalerror(self):
        """
        BUG: `params` só é atribuído DEPOIS da chamada a `_get_user(...)`.
        Se `_get_user` falhar (usuário inválido/inexistente), o bloco
        `except` tenta usar `detail=params` no `UnexpectedEvent.create(...)`,
        mas `params` nunca foi definido -> UnboundLocalError. Isso mascara
        a exceção original (RuntimeError aqui) e o log de erro nem chega a
        ser criado.

        Fix sugerido: mover a criação de `params` para ANTES de
        `user = _get_user(...)`, ou inicializar `params = {}` logo no
        início do `try`.
        """
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.UnexpectedEvent") as MockEvent:
            mock_get_user.side_effect = RuntimeError("boom")

            # Comportamento atual (buggy): não é RuntimeError que propaga,
            # e sim UnboundLocalError.
            with self.assertRaises(UnboundLocalError):
                task_harvest_articles(
                    collection_acron_list=["scl", "mex"],
                    journal_acron_list=["abc"],
                )

        # O log de erro nem chega a ser criado.
        MockEvent.create.assert_not_called()

    def test_exception_after_params_assigned_creates_unexpected_event_and_reraises(self):
        """
        Quando a falha ocorre DEPOIS de `params` já estar definido (ex.:
        dentro da construção do builder ou da iteração de from_harvest),
        o comportamento é o esperado: loga e relança.
        """
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.UnexpectedEvent") as MockEvent:
            mock_get_user.return_value = make_user()
            MockBuilder.return_value.from_harvest.side_effect = RuntimeError("boom")

            with self.assertRaises(RuntimeError):
                task_harvest_articles(
                    collection_acron_list=["scl", "mex"],
                    journal_acron_list=["abc"],
                )

        MockEvent.create.assert_called_once()
        _, kwargs = MockEvent.create.call_args
        self.assertEqual(kwargs["action"], "task_harvest_articles")
        self.assertEqual(kwargs["item"], "scl-mex-abc")
        self.assertIsInstance(kwargs["exception"], RuntimeError)
        self.assertEqual(kwargs["detail"]["collection_acron_list"], ["scl", "mex"])


# =======================================================================
# task_dispatch_articles
# =======================================================================
class TestTaskDispatchArticles(unittest.TestCase):
    def test_dispatches_across_all_three_sources(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.task_process_article_pipeline") as mock_pipeline:
            user = make_user()
            mock_get_user.return_value = user
            builder = MockBuilder.return_value
            builder.from_article_source.return_value = iter([{"article_source_id": 1}])
            builder.from_pid_provider.return_value = iter([{"pp_xml_id": 2}])
            builder.from_article.return_value = iter([{"pp_xml_id": 3}])

            task_dispatch_articles()

        self.assertEqual(mock_pipeline.delay.call_count, 3)
        dispatched_kwargs = [c.kwargs for c in mock_pipeline.delay.call_args_list]
        self.assertEqual(dispatched_kwargs[0]["article_source_id"], 1)
        self.assertEqual(dispatched_kwargs[1]["pp_xml_id"], 2)
        self.assertEqual(dispatched_kwargs[2]["pp_xml_id"], 3)
        for kwargs in dispatched_kwargs:
            self.assertEqual(kwargs["user_id"], user.id)
            self.assertEqual(kwargs["username"], user.username)

    def test_none_items_are_skipped(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.task_process_article_pipeline") as mock_pipeline:
            mock_get_user.return_value = make_user()
            builder = MockBuilder.return_value
            builder.from_article_source.return_value = iter([None])
            builder.from_pid_provider.return_value = iter([None, {"pp_xml_id": 2}])
            builder.from_article.return_value = iter([None])

            task_dispatch_articles()

        self.assertEqual(mock_pipeline.delay.call_count, 1)

    def test_sources_are_passed_their_specific_status_filters(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.task_process_article_pipeline"):
            mock_get_user.return_value = make_user()
            builder = MockBuilder.return_value
            builder.from_article_source.return_value = iter([])
            builder.from_pid_provider.return_value = iter([])
            builder.from_article.return_value = iter([])

            task_dispatch_articles(
                proc_status_list=["todo"],
                data_status_list=["pending"],
                article_source_status_list=["error"],
            )

        builder.from_article_source.assert_called_once_with(
            article_source_status_list=["error"]
        )
        builder.from_pid_provider.assert_called_once_with(proc_status_list=["todo"])
        builder.from_article.assert_called_once_with(data_status_list=["pending"])

    def test_builder_constructed_without_harvest_only_kwargs(self):
        """
        task_dispatch_articles não usa from_harvest, então o builder é
        construído sem limit/timeout/opac_url/stop.
        """
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.task_process_article_pipeline"):
            mock_get_user.return_value = make_user()
            builder = MockBuilder.return_value
            builder.from_article_source.return_value = iter([])
            builder.from_pid_provider.return_value = iter([])
            builder.from_article.return_value = iter([])

            task_dispatch_articles(collection_acron_list=["scl"])

        _, kwargs = MockBuilder.call_args
        for absent_key in ("limit", "timeout", "opac_url", "stop"):
            self.assertNotIn(absent_key, kwargs)

    def test_BUG_get_user_failure_masks_original_exception_with_unboundlocalerror(self):
        """
        Mesmo bug de task_harvest_articles: `params` só é atribuído depois
        de `_get_user(...)`. Se `_get_user` falhar, o `except` tenta usar
        `detail=params` (indefinido) -> UnboundLocalError mascara a
        exceção original e o log de erro nem é criado.
        """
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.UnexpectedEvent") as MockEvent:
            mock_get_user.side_effect = RuntimeError("boom")

            with self.assertRaises(UnboundLocalError):
                task_dispatch_articles(collection_acron_list=["scl"])

        MockEvent.create.assert_not_called()

    def test_exception_after_params_assigned_creates_unexpected_event_and_reraises(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleIteratorBuilder") as MockBuilder, \
             patch(f"{MODULE_PATH}.UnexpectedEvent") as MockEvent:
            mock_get_user.return_value = make_user()
            MockBuilder.return_value.from_article_source.side_effect = RuntimeError("boom")

            with self.assertRaises(RuntimeError):
                task_dispatch_articles(collection_acron_list=["scl"])

        MockEvent.create.assert_called_once()
        _, kwargs = MockEvent.create.call_args
        self.assertEqual(kwargs["action"], "task_dispatch_articles")
        self.assertEqual(kwargs["item"], "scl")


# =======================================================================
# task_process_article_pipeline
# =======================================================================
class TestTaskProcessArticlePipeline(unittest.TestCase):
    def _mock_common(self, MockArticleSource, MockPidProviderXML, mock_load_article):
        article_source = MagicMock()
        article_source.get_pid_provider_xml_id.return_value = 55
        MockArticleSource.objects.get.return_value = article_source

        pp_xml = MagicMock()
        MockPidProviderXML.objects.select_related.return_value.get.return_value = pp_xml

        article = MagicMock(
            is_classic_public=True, valid=True, pid_v3="pid-v3", collections=["c1"]
        )
        mock_load_article.return_value = article
        return article_source, pp_xml, article

    def test_flow_with_article_source_id(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article, \
             patch(f"{MODULE_PATH}.task_export_article_to_articlemeta") as mock_export:
            mock_get_user.return_value = make_user()
            article_source, pp_xml, article = self._mock_common(
                MockArticleSource, MockPidProviderXML, mock_load_article
            )

            task_process_article_pipeline(article_source_id=99)

        MockArticleSource.objects.get.assert_called_once_with(id=99)
        mock_load_article.assert_called_once()
        pp_xml.collections.set.assert_called_once_with(article.collections)
        article.check_availability.assert_called_once()
        mock_export.delay.assert_not_called()

    def test_flow_with_xml_url_creates_article_source(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.Collection") as MockCollection, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article:
            mock_get_user.return_value = make_user()
            MockCollection.get.return_value = "collection-obj"
            article_source = MagicMock()
            article_source.get_pid_provider_xml_id.return_value = 55
            MockArticleSource.create_or_update.return_value = article_source
            MockPidProviderXML.objects.select_related.return_value.get.return_value = MagicMock()
            mock_load_article.return_value = MagicMock(
                is_classic_public=True, valid=True, collections=[]
            )

            task_process_article_pipeline(
                xml_url="http://x/y.xml",
                collection_acron="scl",
                pid="S123",
                source_date="2024-01-01",
            )

        MockArticleSource.create_or_update.assert_called_once()
        _, kwargs = MockArticleSource.create_or_update.call_args
        self.assertEqual(kwargs["url"], "http://x/y.xml")
        self.assertEqual(kwargs["pid"], "S123")
        self.assertEqual(kwargs["collection"], "collection-obj")
        MockCollection.get.assert_called_once_with("scl")

    def test_flow_with_pp_xml_id_direct_skips_article_source(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article:
            mock_get_user.return_value = make_user()
            MockPidProviderXML.objects.select_related.return_value.get.return_value = MagicMock()
            mock_load_article.return_value = MagicMock(
                is_classic_public=True, valid=True, collections=[]
            )

            task_process_article_pipeline(pp_xml_id=123)

        MockArticleSource.objects.get.assert_not_called()
        MockArticleSource.create_or_update.assert_not_called()
        MockPidProviderXML.objects.select_related.return_value.get.assert_called_once_with(
            id=123
        )

    def test_export_dispatched_when_classic_public_and_valid(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article, \
             patch(f"{MODULE_PATH}.task_export_article_to_articlemeta") as mock_export:
            user = make_user()
            mock_get_user.return_value = user
            self._mock_common(MockArticleSource, MockPidProviderXML, mock_load_article)

            task_process_article_pipeline(
                article_source_id=1,
                export_to_articlemeta=True,
                collection_acron_list=["scl"],
            )

        mock_export.delay.assert_called_once_with(
            pid_v3="pid-v3",
            collection_acron_list=["scl"],
            force_update=None,
            user_id=user.id,
            username=user.username,
        )

    def test_export_skipped_when_not_classic_public(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article, \
             patch(f"{MODULE_PATH}.task_export_article_to_articlemeta") as mock_export:
            mock_get_user.return_value = make_user()
            article_source, pp_xml, article = self._mock_common(
                MockArticleSource, MockPidProviderXML, mock_load_article
            )
            article.is_classic_public = False

            result = task_process_article_pipeline(
                article_source_id=1, export_to_articlemeta=True
            )

        mock_export.delay.assert_not_called()
        self.assertIsNone(result)

    def test_export_skipped_when_not_valid(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article, \
             patch(f"{MODULE_PATH}.task_export_article_to_articlemeta") as mock_export:
            mock_get_user.return_value = make_user()
            article_source, pp_xml, article = self._mock_common(
                MockArticleSource, MockPidProviderXML, mock_load_article
            )
            article.valid = False

            task_process_article_pipeline(
                article_source_id=1, export_to_articlemeta=True
            )

        mock_export.delay.assert_not_called()

    def test_check_availability_force_update_true_when_export_flag_set(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article, \
             patch(f"{MODULE_PATH}.task_export_article_to_articlemeta"):
            mock_get_user.return_value = make_user()
            article_source, pp_xml, article = self._mock_common(
                MockArticleSource, MockPidProviderXML, mock_load_article
            )

            task_process_article_pipeline(
                article_source_id=1, export_to_articlemeta=True, force_update=False
            )

        _, kwargs = article.check_availability.call_args
        self.assertTrue(kwargs["force_update"])

    def test_check_availability_force_update_false_when_no_flags(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.ArticleSource") as MockArticleSource, \
             patch(f"{MODULE_PATH}.PidProviderXML") as MockPidProviderXML, \
             patch(f"{MODULE_PATH}.load_article") as mock_load_article, \
             patch(f"{MODULE_PATH}.task_export_article_to_articlemeta"):
            mock_get_user.return_value = make_user()
            article_source, pp_xml, article = self._mock_common(
                MockArticleSource, MockPidProviderXML, mock_load_article
            )

            task_process_article_pipeline(
                article_source_id=1, export_to_articlemeta=False, force_update=False
            )

        _, kwargs = article.check_availability.call_args
        self.assertFalse(kwargs["force_update"])

    # -------------------------------------------------------------
    # BUG: exceções são logadas mas NUNCA relançadas nesta task
    # -------------------------------------------------------------
    def test_BUG_generic_exception_is_logged_but_not_reraised(self):
        """
        BUG: ao contrário de task_harvest_articles e task_dispatch_articles
        (que fazem `raise` no final do except), task_process_article_pipeline
        NÃO relança a exceção depois de chamar UnexpectedEvent.create. Isso
        faz a task Celery terminar como SUCCESS mesmo quando falhou —
        sem retry automático e sem aparecer como falha em monitoramento.

        Fix sugerido: adicionar `raise` ao final do bloco `except`, igual
        às outras duas tasks.
        """
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.UnexpectedEvent") as MockEvent:
            mock_get_user.side_effect = RuntimeError("boom")

            # Não levanta exceção — comportamento atual (buggy).
            result = task_process_article_pipeline(xml_url="http://x")

        MockEvent.create.assert_called_once()
        self.assertIsNone(result)

    def test_BUG_missing_collection_acron_validation_error_is_swallowed(self):
        """
        Mesma causa-raiz do bug acima: o ValueError de validação
        ("collection_acron is required...") é logado via UnexpectedEvent
        mas não propaga — quem chamou a task não sabe que ela falhou.
        """
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.UnexpectedEvent") as MockEvent:
            mock_get_user.return_value = make_user()

            result = task_process_article_pipeline(xml_url="http://x", pid="S1")
            # sem collection_acron -> ValueError interno, mas não propaga

        self.assertIsNone(result)
        MockEvent.create.assert_called_once()
        _, kwargs = MockEvent.create.call_args
        self.assertIn("collection_acron is required", str(kwargs["exception"]))

    def test_BUG_no_entry_point_validation_error_is_swallowed(self):
        with patch(f"{MODULE_PATH}._get_user") as mock_get_user, \
             patch(f"{MODULE_PATH}.UnexpectedEvent") as MockEvent:
            mock_get_user.return_value = make_user()

            result = task_process_article_pipeline()

        self.assertIsNone(result)
        MockEvent.create.assert_called_once()
        _, kwargs = MockEvent.create.call_args
        self.assertIn("No valid entry point", str(kwargs["exception"]))


if __name__ == "__main__":
    unittest.main()