import logging

from celery import group
from django.db.models import Count, Q

from config import celery_app
from editorialboard import choices
from editorialboard.models import EditorialBoardHTML
from editorialboard.sources.classic_website import (
    extract_edboard_section,
    fetch_edboard_html,
)
from editorialboard.sources.editors_anchor import extract_editors_anchor_section
from journal.models import SciELOJournal

logger = logging.getLogger(__name__)


def get_scielo_journals_queryset(
    collection_acron_list=None,
    exclude_collection_acron_list=None,
    only_missing=False,
):
    queryset = (
        SciELOJournal.objects.filter(
            collection__is_active=True,
            collection__domain__isnull=False,
            journal_acron__isnull=False,
        )
        .exclude(collection__domain="")
        .exclude(journal_acron="")
    )

    if collection_acron_list:
        queryset = queryset.filter(collection__acron3__in=collection_acron_list)
    if exclude_collection_acron_list:
        queryset = queryset.exclude(
            collection__acron3__in=exclude_collection_acron_list
        )
    if only_missing:
        queryset = queryset.annotate(
            ok_languages=Count(
                "editorial_board_html",
                filter=Q(editorial_board_html__status=choices.EDBOARD_FETCH_STATUS_OK),
            )
        ).filter(ok_languages__lt=len(choices.EDBOARD_LANGUAGES_HTML_CLASSIC_WEBSITE))
    return queryset


@celery_app.task(bind=True)
def collect_editorial_board_html(
    self,
    user_id=None,
    username=None,
    collection_acron_list=None,
    exclude_collection_acron_list=None,
    only_missing=False,
    editors_anchor_collection_acron_list=None,
):
    """
    Dispara uma task filha por SciELOJournal para coletar o HTML do corpo editorial.

    Args:
        collection_acron_list: coleções a incluir (lista ou "scl,mex")
        exclude_collection_acron_list: coleções a excluir (lista ou "scl,mex")
        only_missing: ignora periódicos que já têm o HTML coletado com sucesso
        editors_anchor_collection_acron_list: coleções cuja página tem a âncora
            #editors (ex. ["scl"]). As demais, como o México, seguem o
            recorte do site clássico.
    """
    logging.info("Iniciando coleta HTML do corpo editorial das colecoes do site classico")
    editors_anchor_collections = set(editors_anchor_collection_acron_list or [])
    scielo_journals = list(
        get_scielo_journals_queryset(
            collection_acron_list=collection_acron_list,
            exclude_collection_acron_list=exclude_collection_acron_list,
            only_missing=only_missing,
        ).values_list("id", "collection__acron3")
    )
    if not scielo_journals:
        logger.warning("No SciELO journals found to collect editorial board HTML")
        return None

    group(
        fetch_editorial_board_html.s(
            scielo_journal_id=scielo_journal_id,
            user_id=user_id,
            username=username,
            editors_anchor=collection_acron in editors_anchor_collections,
        )
        for scielo_journal_id, collection_acron in scielo_journals
    ).apply_async()
    logger.info(
        f"Started collecting editorial board HTML for "
        f"{len(scielo_journals)} SciELO journals"
    )


@celery_app.task(bind=True)
def fetch_editorial_board_html(
    self, scielo_journal_id, user_id=None, username=None, editors_anchor=False
):
    scielo_journal = SciELOJournal.objects.select_related("collection").get(
        id=scielo_journal_id
    )
    extract = extract_editors_anchor_section if editors_anchor else extract_edboard_section
    saved = []
    for result in fetch_edboard_html(
        scielo_journal.collection.base_url, scielo_journal.journal_acron
    ):
        raw_html = result["raw_html"]
        obj = EditorialBoardHTML.record(
            scielo_journal,
            result["language"],
            source_url=result["source_url"],
            http_status=result["http_status"],
            raw_html=raw_html,
            edboard_html=extract(raw_html) if raw_html else None,
        )
        saved.append({"id": obj.id, "status": obj.status, "language": obj.language})
    return saved
