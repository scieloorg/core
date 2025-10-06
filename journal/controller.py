import json
import logging
import sys
import traceback

from core.mongodb import write_item
from core.utils import date_utils
from journal.models import Journal, JournalExporter
from tracker.models import UnexpectedEvent


def export_journal_to_articlemeta(
    user,
    journal,
    collection_acron_list=None,
    force_update=None,
    version=None,
):
    try:
        events = None
        logging.info("....")
        if not journal:
            raise ValueError("export_journal_to_articlemeta requires journal")
        for legacy_keys in journal.get_legacy_keys(
            collection_acron_list, is_active=True
        ):
            try:
                exporter = None
                response = None
                events = []
                col = legacy_keys.get("collection")
                pid = legacy_keys.get("pid")
                logging.info(legacy_keys)
                events.append("check articlemeta exportation demand")
                logging.info(
                    (user, journal, "articlemeta", pid, col, version, force_update)
                )
                exporter = JournalExporter.get_demand(
                    user, journal, "articlemeta", pid, col, version, force_update
                )
                if not exporter:
                    # não encontrou necessidade de exportar
                    continue

                events.append("building articlemeta format for journal")
                journal_data = journal.articlemeta_format(col.acron3)
                response = str(journal_data)

                try:
                    json.dumps(journal_data)
                except Exception as e:
                    logging.exception(e)
                    response = str(journal_data)
                    raise e

                events.append("writing journal to articlemeta database")
                response = write_item("journals", journal_data)

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
                        response=response,
                        errors=None,
                        exceptions=traceback.format_exc(),
                    )
                else:
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "operation": "export_article_to_articlemeta",
                            "journal": str(journal),
                            "collection": str(col),
                            "events": events,
                            "traceback": traceback.format_exc(),
                        },
                    )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "export_journal_to_articlemeta",
                "journal": journal,
                "collection_acron_list": collection_acron_list,
                "force_update": force_update,
                "events": events,
            },
        )


def bulk_export_journals_to_articlemeta(
    user=None,
    collection_acron_list=None,
    journal_acron_list=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=None,
    version=None,
):
    """
    Export journals to ArticleMeta Database with flexible filtering.

    Args:
        collections: List of collections acronyms (e.g., ["scl", "mex"])
        from_date: Export articles from this date
        until_date: Export articles until this date
        days_to_go_back: Export articles from this number of days ago
        force_update: Force update existing records
        user: User object
        client: MongoDB client object
    """
    queryset = Journal.select_items(
        collection_acron_list=collection_acron_list,
        journal_acron_list=journal_acron_list,
        from_date=from_date,
        until_date=until_date,
        days_to_go_back=days_to_go_back,
    )

    for journal in queryset.iterator():
        export_journal_to_articlemeta(
            user,
            journal=journal,
            collection_acron_list=collection_acron_list,
            force_update=force_update,
            version=version,
        )
