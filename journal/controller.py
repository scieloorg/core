import logging
import sys

from core.mongodb import write_to_db
from core.utils import date_utils
from journal.models import SciELOJournal, SciELOJournalExport
from tracker.models import UnexpectedEvent


def export_journal_to_articlemeta(
    issn,
    force_update=True, 
    user=None,
    client=None,
):
    """
    Export journal to ArticleMeta

    Args:
        issn (str): ISSN of the journal
        force_update (bool): Force update if journal already exported to ArticleMeta
        user (User): User object for logging
        client (MongoClient): MongoDB client object

    Returns:
        bool: True if export was successful, False otherwise
    """
    if not issn:
        logging.error("ISSN is required for exporting journal to ArticleMeta")
        return False
    
    try:
        sj = SciELOJournal.objects.get(issn_scielo=issn)
    except SciELOJournal.DoesNotExist:
        logging.error(f"SciELO Journal with issn_scielo {issn} does not exist.")
        return False
    
    if not force_update and SciELOJournalExport.is_exported(sj, 'articlemeta', sj.collection):
        logging.info(f"SciELO Journal {sj.issn_scielo} already exported to ArticleMeta")
        return True
    
    # Prepare journal data in ArticleMeta format
    try:
        sj_data = sj.journal.articlemeta_format(sj.collection.acron3)
    except Exception as e:
        logging.error(f"Error converting journal data to ArticleMeta format for journal {sj.issn_scielo}: {e}")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "export_journal_to_articlemeta",
                "scielo_journal_id": sj.pk,
                "issn": issn,
                "force_update": force_update,
            },
        )
        return False
    
    # Write journal data to MongoDB
    try:
        success = write_to_db(
            data=sj_data, 
            database="articlemeta", 
            collection="journals", 
            force_update=force_update,
            client=client,
        )
        if success:
            SciELOJournalExport.mark_as_exported(sj, 'articlemeta', sj.collection, user)
    except Exception as e:
        logging.error(f"Error writing journal data to MongoDB for journal {sj.issn_scielo}: {e}")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "export_journal_to_articlemeta",
                "scielo_journal_id": sj.pk,
                "issn": issn,
                "force_update": force_update,
            },
        )
        return False
    
    return True


def bulk_export_journals_to_articlemeta(
    collections=[],
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=True,
    user=None,
    client=None,
):
    """
    Export journals to ArticleMeta Database with flexible filtering.
    
    Args:
        collections: Filter by collections acronyms (e.g., ['scl', 'mex'])
        from_date: Export articles from this date
        until_date: Export articles until this date
        days_to_go_back: Export articles from this number of days ago
        force_update: Force update existing records
        user: User object
        client: MongoDB client object
    """
    filters = {}
    
    # Collection filter
    if collections:
        filters['collection__acron3__in'] = collections

    # Date filters
    if from_date or until_date or days_to_go_back:
        from_date_str, until_date_str = date_utils.get_date_range(from_date, until_date, days_to_go_back)
        filters['updated__range'] = (from_date_str, until_date_str)

    # Build queryset with filters
    queryset = SciELOJournal.objects.filter(**filters)
        
    logging.info(f"Starting export of {queryset.count()} journals to ArticleMeta.")
    
    for sj in queryset.iterator():
        export_journal_to_articlemeta(
            issn=sj.issn_scielo,
            force_update=force_update,
            user=user,
            client=client,
        )

    logging.info(f"Export completed.")
