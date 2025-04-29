from journal.models import SciELOJournal, TitleInDatabase
from core.utils.api_articlemeta_format import add_to_result, add_items

def get_articlemeta_format_issue(obj):
    result = {}

    scielo_issn = SciELOJournal.objects.filter(journal=obj.journal).first().issn_scielo

    add_to_result("v30", obj.journal.short_title, result)
    add_to_result("v31", obj.volume, result)
    add_to_result("v32", obj.number, result)
    add_to_result("v35", scielo_issn, result)
    add_items("v62", [ch.get_institution_name for ch in obj.journal.copyright_holder_history.all()], result)

    # Data de publicação do fascículo
    year = obj.year
    month = obj.month
    if year and month:
        add_to_result("v64", year + month, result)
    elif year:
        add_to_result("v64", year, result)
    add_to_result("v117", obj.journal.standard.code if obj.journal.standard else None, result)
    add_to_result("v130", obj.journal.title if obj.journal.title else None, result)
    add_items("v140", [sponsor.get_institution_name for sponsor in obj.journal.sponsor_history.all()], result)
    add_to_result("v151", obj.journal.official.iso_short_title if obj.journal.official and obj.journal.official.iso_short_title else None, result)
    add_items("v230", [pt.text for pt in obj.journal.official.parallel_titles if obj.journal.official and pt.text], result)
    medline_titles = TitleInDatabase.objects.filter(journal=obj.journal, indexed_at__acronym__iexact="medline")
    add_items("v421", [medline.title for medline in medline_titles], result)
    
    add_items("v480", [publisher.get_institution_name for publisher in obj.journal.publisher_history.all()], result)
    
    return result
