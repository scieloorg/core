import csv
import json
import logging
import sys
import traceback

from django.db.models import F, Q
from packtools.sps.formats.am import am

from article.models import Article, ArticleExporter, ArticleFunding, ArticleSource
from article import choices
from collection.models import Collection
from core.mongodb import write_item
from core.utils.harvesters import AMHarvester, OPACHarvester
from institution.models import Sponsor
from journal.models import SciELOJournal
from pid_provider import choices as pid_provider_choices
from pid_provider.models import PidProviderXML
from tracker.models import UnexpectedEvent


class ArticleIsNotAvailableError(Exception): ...


def load_financial_data(row, user):
    article_findings = []
    for institution in row.get("funding_source").split(","):
        sponsor = Sponsor.get_or_create(
            user=user,
            name=institution,
            acronym=None,
            level_1=None,
            level_2=None,
            level_3=None,
            location=None,
            official=None,
            is_official=None,
            url=None,
            institution_type=None,
        )
        article_findings.append(
            ArticleFunding.get_or_create(
                award_id=row.get("award_id"), funding_source=sponsor, user=user
            )
        )
    article = Article.get_or_create(
        pid_v2=row.get("pid_v2"), fundings=article_findings, user=user
    )

    return article


def read_file(user, file_path):
    with open(file_path, "r") as csvfile:
        data = csv.DictReader(csvfile)
        for row in data:
            logging.debug(row)
            load_financial_data(row, user)


def export_article_to_articlemeta(
    user,
    article,
    collection_acron_list=None,
    force_update=None,
    version=None,
) -> bool:

    try:
        events = []
        if not article.classic_available(collection_acron_list):
            raise ArticleIsNotAvailableError(
                f"Article {article} {collection_acron_list} (classic) is not available. Unable to export to ArticleMeta."
            )

        new_available = article.new_available(collection_acron_list).exists()
        events.append(f"Article new {article} {collection_acron_list} {new_available}")

        events.append(
            f"export_article_to_articlemeta: {article}, collections: {collection_acron_list}, force_update: {force_update}"
        )
        legacy_keys_items = list(article.get_legacy_keys(
            collection_acron_list, is_active=True
        ))
        events.append(f"Legacy keys to process: {legacy_keys_items}")
        if not legacy_keys_items:
            raise ValueError("No legacy keys found for article")

        external_data = {
            "created_at": article.created.strftime("%Y-%m-%d"),
            "document_type": article.article_type,
            "processing_date": article.updated.strftime("%Y-%m-%d"),
            "publication_date": article.pub_date,
            "publication_year": article.issue.year,
            "version": "xml",
        }
        if new_available:
            external_data["pid_v3"] = article.pid_v3

        text_langs = article.get_text_langs()
        
        article_data = {}
        for legacy_keys in legacy_keys_items:
            col = legacy_keys.get("collection")
            pid = legacy_keys.get("pid")
            item = f"{pid}-{col}"
            try:
                exporter = None
                response = None
                events = []
                data = {}
                
                if not article_data:
                    events.append("building articlemeta format for article")
                    article_data = am.build(article.xmltree, external_data)

                events.append("check articlemeta exportation demand")
                exporter = ArticleExporter.get_demand(
                    user, article, "articlemeta", pid, col, version, force_update
                )
                if not exporter:
                    # não encontrou necessidade de exportar
                    continue

                data = {"collection": col.acron3}
                data.update(article_data)
                data["article"]["fulltext_langs"] = text_langs.get(col.acron3, {})

                events.append("building articlemeta format for issue")
                issue_data = article.issue.articlemeta_format(col.acron3)
                data.update(issue_data)

                events.append("updating articlemeta format with issue data")
                # Issue data
                data["code_issue"] = issue_data["code"]
                data["issue"] = issue_data["issue"]

                # Journal data
                events.append("updating articlemeta format with journal data")
                data["code_title"] = [
                    x for x in issue_data["code_title"] if x is not None
                ]
                data["title"] = issue_data["title"]
                data["code"] = pid or article.pid_v2
                data.update(external_data)

                if not data["article"]:
                    raise ValueError("Missing 'article' in data")

                try:
                    json.dumps(data)
                    data["code"]
                except Exception as e:
                    response = str(data)
                    raise e

                # Export the article to ArticleMeta
                events.append("writing article to articlemeta database")
                response = write_item("articles", data)

                # Mark the article as exported to ArticleMeta in the collection
                exporter.finish(
                    user,
                    completed=True,
                    events=events,
                    response=response,
                    errors=None,
                    exceptions=None,
                )

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if exporter:
                    exporter.finish(
                        user,
                        completed=False,
                        events=events,
                        response=response or str(data),
                        errors=None,
                        exceptions=traceback.format_exc(),
                    )
                else:
                    UnexpectedEvent.create(
                        action="export_article_to_articlemeta",
                        item=item,
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "article": str(article),
                            "legacy_keys": str(legacy_keys),
                            "events": events,
                            "traceback": traceback.format_exc(),
                        },
                    )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            action="export_article_to_articlemeta",
            item=str(article),
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "collection_acron_list": collection_acron_list,
                "force_update": force_update,
                "traceback": traceback.format_exc(),
            },
        )


def bulk_export_articles_to_articlemeta(
    user,
    collection_acron_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=None,
    version=None,
):
    """
    Bulk export articles to ArticleMeta.

    Args:
        user: User object
        collection_acron_list: List of collection acronyms to filter articles
        journal_acron_list: List of journal acronyms to filter articles
        from_pub_year: Start publication year to filter articles
        until_pub_year: End publication year to filter articles
        from_date: Start date to filter articles
        until_date: End date to filter articles
        days_to_go_back: Number of days to go back from today or until_date
        force_update: Whether to force update the export. Defaults to True
        version: Version identifier for export

    Returns:
        bool: True if the export was successful, False otherwise
    """
    try:
        params = {}
        if not force_update:
            # seleciona os artigos considerados publicados
            params = {
                "is_classic_public": True,
            }
        queryset = Article.select_items(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_pub_year=from_pub_year,
            until_pub_year=until_pub_year,
            from_updated_date=from_date,
            until_updated_date=until_date,
            params=params
        )
        if not queryset.exists():
            args = dict(
                collection_acron_list=collection_acron_list,
                journal_acron_list=journal_acron_list,
                from_pub_year=from_pub_year,
                until_pub_year=until_pub_year,
                from_updated_date=from_date,
                until_updated_date=until_date,
                params=params,
            )
            raise ValueError(f"No articles found. Arguments: {args}")

        for article in queryset.select_related("journal", "journal__official", "pp_xml").iterator():
            try:
                if force_update:
                    article.check_availability(user)
                if not article.is_classic_public:
                    continue
                export_article_to_articlemeta(
                    user,
                    article=article,
                    collection_acron_list=collection_acron_list,
                    force_update=force_update,
                    version=version,
                )
            except Exception as e:
                # Registra erro do article mas continua processando outros
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    action="bulk_export_articles_to_articlemeta",
                    item=str(article),
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "collection_acron_list": collection_acron_list,
                        "version": version,
                        "force_update": force_update,
                    },
                )
                continue
        
        return True
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            action="bulk_export_articles_to_articlemeta",
            item="",
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_date": str(from_date) if from_date else None,
                "until_date": str(until_date) if until_date else None,
                "days_to_go_back": days_to_go_back,
                "force_update": force_update,
            },
        )
        raise


class ArticleIteratorBuilder:
    """
    Constrói iteradores de seleção de artigos para despacho ao pipeline
    (``task_process_article_pipeline``).

    O ``__init__`` guarda apenas os filtros COMUNS a mais de uma fonte
    (usuário, coleção/periódico, intervalo de datas/anos, força de
    atualização, parâmetros de harvest). Os filtros que são exclusivos de
    uma única fonte (``proc_status_list``, ``data_status_list``,
    ``article_source_status_list``) NÃO ficam no ``__init__`` — são passados
    diretamente ao método correspondente, o que deixa explícito qual fonte
    está sendo usada em cada chamada.

    Cada método ``from_*``:
      - usa os atributos comuns já armazenados na instância;
      - retorna um gerador independente que yields kwargs prontos para
        ``task_process_article_pipeline``;
      - representa exatamente UM ponto de entrada do pipeline.

    Mutuamente excludentes por construção: a classe não tem mais um
    ``__iter__`` que decide sozinha quais iteradores ativar e os roda em
    sequência. Quem chama (normalmente ``task_dispatch_articles``) escolhe
    explicitamente UM método por execução. Isso elimina a possibilidade de
    dois iteradores selecionarem o mesmo artigo/``pp_xml_id`` na mesma
    chamada.

    Uso::

        builder = ArticleIteratorBuilder(
            user=user,
            collection_acron_list=["scl"],
        )
        for kwargs in builder.from_pid_provider(proc_status_list=["todo"]):
            task_process_article_pipeline.delay(**kwargs)
    """

    def __init__(
        self,
        user,
        collection_acron_list=None,
        journal_acron_list=None,
        from_pub_year=None,
        until_pub_year=None,
        from_date=None,
        until_date=None,
        force_update=None,
        limit=None,
        timeout=None,
        opac_url=None,
        stop=None,
    ):
        self.user = user
        self.collection_acron_list = collection_acron_list
        self.journal_acron_list = journal_acron_list
        self.from_pub_year = from_pub_year
        self.until_pub_year = until_pub_year
        self.from_date = from_date
        self.until_date = until_date
        self.force_update = force_update
        self.limit = limit
        self.timeout = timeout
        self.opac_url = opac_url
        self.stop = stop

    # ------------------------------------------------------------------
    # from_pid_provider
    # ------------------------------------------------------------------
    def from_pid_provider(self, proc_status_list=None):
        filters = {
            "proc_status__in": proc_status_list or [pid_provider_choices.PPXML_STATUS_TODO],
        }
        if self.from_date:
            filters["updated__gte"] = self.from_date
        if self.until_date:
            filters["updated__lte"] = self.until_date
        if self.from_pub_year:
            filters["pub_year__gte"] = self.from_pub_year
        if self.until_pub_year:
            filters["pub_year__lte"] = self.until_pub_year

        params = {}
        if self.collection_acron_list:
            params["collection__acron3__in"] = self.collection_acron_list
        if self.journal_acron_list:
            params["journal_acron__in"] = self.journal_acron_list

        q = Q()
        if params:
            journal_issns = SciELOJournal.objects.select_related(
                "journal__official"
            ).filter(
                **params
            ).values_list(
                "journal__official__issn_print", "journal__official__issn_electronic"
            ).distinct()

            issn_list = set()
            for issn_print, issn_electronic in journal_issns:
                if issn_print:
                    issn_list.add(issn_print)
                if issn_electronic:
                    issn_list.add(issn_electronic)

            q = Q(issn_print__in=issn_list) | Q(issn_electronic__in=issn_list)
        qs = (
            PidProviderXML.objects.filter(q, **filters)
            .order_by("-updated")
            .values(pp_xml_id=F("id"))
            .distinct()
        )

        yield from qs.iterator()

    # ------------------------------------------------------------------
    # from_article
    # ------------------------------------------------------------------
    def from_article(self, data_status_list=None):
        """
        Itera Article pendentes ou com erro.
        """
        filters = {}
        if data_status_list:
            filters["data_status__in"] = data_status_list
        if self.collection_acron_list:
            filters["journal__scielojournal__collection__acron3__in"] = (
                self.collection_acron_list
            )
        if self.journal_acron_list:
            filters["journal__scielojournal__journal_acron__in"] = (
                self.journal_acron_list
            )
        if self.from_pub_year:
            filters["pub_date_year__gte"] = self.from_pub_year
        if self.until_pub_year:
            filters["pub_date_year__lte"] = self.until_pub_year
        if self.from_date:
            filters["updated__gte"] = self.from_date
        if self.until_date:
            filters["updated__lte"] = self.until_date

        filters["valid"] = False
        base_qs = Article.objects.filter(**filters).distinct()

        # Artigos que já têm pp_xml: values() já entrega o dict pronto.
        yield from base_qs.filter(pp_xml__isnull=False).values("pp_xml_id").iterator()

    # ------------------------------------------------------------------
    # from_article_source
    # ------------------------------------------------------------------
    def from_article_source(self, article_source_status_list=None):
        """
        Itera ArticleSources pendentes ou com erro.

        Otimização: ``.values(article_source_id=F("id"))`` sobre a
        queryset retornada por ``get_queryset_to_complete_data`` já
        entrega o dict pronto — sem instanciar cada ArticleSource
        completo (não precisamos de mais nenhum campo do objeto para
        montar o kwarg de despacho).
        """
        params = {}
        if article_source_status_list:
            params["status__in"] = article_source_status_list
        if self.from_date:
            params["updated__gte"] = self.from_date
        if self.until_date:
            params["updated__lte"] = self.until_date

        if self.force_update:
            qs = Q()
        else:
            qs = (
                Q(pid_provider_xml__proc_status__in=pid_provider_choices.PPXML_STATUS_TO_CREATE_OR_UPDATE_ARTICLE_SOURCE) |
                Q(pid_provider_xml__isnull=True) | Q(file__isnull=True)
            )
        yield from ArticleSource.objects.filter(
            qs,
            **params,
        ).values(article_source_id=F("id")).iterator()

    # ------------------------------------------------------------------
    # from_harvest
    # ------------------------------------------------------------------
    def from_harvest(self):
        """Itera documentos coletados via OPAC ou ArticleMeta."""
        if Collection.objects.count() == 0:
            Collection.load(self.user)

        params = {}
        if self.collection_acron_list:
            params["collection__acron3__in"] = self.collection_acron_list
        if self.journal_acron_list:
            params["journal_acron__in"] = self.journal_acron_list

        collection_and_journal_items = SciELOJournal.objects.select_related(
            "collection"
        ).filter(
            **params
        ).values_list(
            "collection__acron3", "journal_acron", "issn_scielo"
        ).distinct()

        for collection_acron, journal_acron, issn_scielo in collection_and_journal_items:
            harvester = self._build_harvester(collection_acron, journal_acron, issn_scielo)
            for document in harvester.harvest_documents():
                yield {
                    "xml_url": document["url"],
                    "collection_acron": collection_acron,
                    "pid": document["pid_v2"],
                    "source_date": document.get("processing_date") or document.get("origin_date"),
                    "is_public": document.get("is_public"),
                    "document": document,
                }

    def _build_harvester(self, collection_acron, journal_acron=None, journal_id=None):
        """Instancia o harvester adequado para a coleção."""
        kwargs = dict(
            from_date=self.from_date,
            until_date=self.until_date,
            limit=self.limit,
            timeout=self.timeout,
        )
        if collection_acron == "scl":
            if journal_acron:
                kwargs["journal"] = journal_acron
            if self.stop:
                kwargs["stop"] = self.stop
            return OPACHarvester(self.opac_url or "https://www.scielo.br", collection_acron, **kwargs)
        if journal_id:
            kwargs["journal"] = journal_id
        return AMHarvester("article", collection_acron, **kwargs)
