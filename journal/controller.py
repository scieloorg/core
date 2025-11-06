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
        
        logging.info(
            f"export_journal_to_articlemeta: {journal}, collections: {collection_acron_list}, force_update: {force_update}"
        )
        legacy_keys_items = list(journal.get_legacy_keys(
            collection_acron_list, is_active=True
        ))
        logging.info(f"Legacy keys to process: {legacy_keys_items}")
        if not legacy_keys_items:
            UnexpectedEvent.create(
                exception=ValueError("No legacy keys found for journal"),
                detail={
                    "operation": "export_journal_to_articlemeta",
                    "journal": str(journal),
                    "collection_acron_list": collection_acron_list,
                    "force_update": force_update,
                    "events": events,
                },
            )
            return
        for legacy_keys in legacy_keys_items:
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
        user: User object for authentication
        collection_acron_list: List of collections acronyms (e.g., ["scl", "mex"])
        journal_acron_list: List of journal acronyms to filter
        from_date: Export journals modified from this date
        until_date: Export journals modified until this date
        days_to_go_back: Export journals modified from this number of days ago
        force_update: Force update existing records
        version: Version identifier for export
    """
    try:
        queryset = Journal.select_items(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_date=from_date,
            until_date=until_date,
            days_to_go_back=days_to_go_back,
        )
        if not queryset.exists():
            UnexpectedEvent.create(
                exception=ValueError("No journals found for the given filters"),
                detail={
                    "function": "bulk_export_journals_to_articlemeta",
                    "collection_acron_list": collection_acron_list,
                    "journal_acron_list": journal_acron_list,
                    "from_date": str(from_date) if from_date else None,
                    "until_date": str(until_date) if until_date else None,
                    "days_to_go_back": days_to_go_back,
                    "force_update": force_update,
                },
            )
            return

        for journal in queryset.iterator():
            try:
                export_journal_to_articlemeta(
                    user,
                    journal=journal,
                    collection_acron_list=collection_acron_list,
                    force_update=force_update,
                    version=version,
                )
            except Exception as e:
                # Registra erro do journal mas continua processando outros
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "function": "bulk_export_journals_to_articlemeta",
                        "journal": str(journal),
                        "force_update": force_update,
                    },
                )
                continue
                
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "bulk_export_journals_to_articlemeta",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "from_date": str(from_date) if from_date else None,
                "until_date": str(until_date) if until_date else None,
                "days_to_go_back": days_to_go_back,
                "force_update": force_update,
            },
        )
        raise
