from collections import defaultdict

from core.utils.articlemeta_dict_utils import add_items, add_to_result
from journal.models import SciELOJournal, TitleInDatabase
from article.models import Article

def get_articlemeta_format_issue(obj):
    result = defaultdict(list)

    scielo_journal = SciELOJournal.objects.filter(journal=obj.journal).first()

    add_to_result("v30", obj.journal.short_title, result)
    add_to_result("v31", obj.volume, result)
    add_to_result("v32", obj.number, result)
    add_items("v33", [title for title in obj.issue_title.all()], result)
    add_to_result("v35", scielo_journal.issn_scielo, result)
    
    # Dado fixo v48
    result['v48'].append({'h': 'Sumário', 'l': 'pt', '_': ''}, {'h': 'Table of Contents', 'l': 'en', '_': ''}, {'h': 'Sumario', 'l': 'es', '_': ''})

    add_items("v62", [ch.get_institution_name for ch in obj.journal.copyright_holder_history.all()], result)

    # Data de publicação do fascículo
    year = obj.year
    month = obj.month
    if year and month:
        result["v64"].append({"a": year, "m": month})
        add_to_result("v65", year + month + '00', result)
    elif year:
        result["v64"].append({"a": year})
        add_to_result("v65", year + '0000', result)

    if obj.journal and obj.journal.vocabulary:
        add_to_result("v85", obj.journal.vocabulary.acronym, result)
    add_to_result("v91", obj.created.strftime("%Y-%m-%d"), result)
    add_to_result("v117", obj.journal.standard.code if obj.journal.standard else None, result)
    add_to_result("v122", Article.objects.count(), result)
    add_to_result("v130", obj.journal.title if obj.journal.title else None, result)
    if not obj.number:
        add_to_result("v131", obj.supplement, result)
    else:
        add_to_result("v132", obj.supplement, result)

    add_to_result("v200", '0', result)
    add_items("v140", [sponsor.get_institution_name for sponsor in obj.journal.sponsor_history.all()], result)
    add_to_result("v151", obj.journal.official.iso_short_title if obj.journal.official and obj.journal.official.iso_short_title else None, result)
    add_items("v230", [pt.text for pt in obj.journal.official.parallel_titles if obj.journal.official and pt.text], result)
    medline_titles = TitleInDatabase.objects.filter(journal=obj.journal, indexed_at__acronym__iexact="medline")
    add_items("v421", [medline.title for medline in medline_titles], result)
    
    add_items("v480", [publisher.get_institution_name for publisher in obj.journal.publisher_history.all()], result)
    add_to_result("700", '0', result)
    add_to_result("701", '1', result)
    add_to_result("706", 'i', result)
    add_to_result("v930", scielo_journal.journal_acron, result)
    add_to_result("991", '1', result)
    
    return result
