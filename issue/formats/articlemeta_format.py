from collections import defaultdict

from core.utils.articlemeta_dict_utils import add_items, add_to_result
from journal.models import SciELOJournal, TitleInDatabase
from article.models import Article

def get_articlemeta_format_issue(obj):
    result = defaultdict(list)

    scielo_journal = SciELOJournal.objects.filter(journal=obj.journal).first()

    path_to_base_issue(obj, result)
    short_title(obj, result)
    volume(obj, result)
    number(obj, result)
    issue_title(obj, result)
    part(obj, result)
    issn(scielo_journal, result)
    title_of_issue(obj, result)
    status_issue(obj, result)
    legend_bibliographic(obj, result)
    # Dado fixo v48
    title_summary(obj, result)
    editora(obj, result)
    publication_date(obj, result)
    publication_date_normalized(obj, result)
    vocabulary_control(obj, result)

    date_of_inclusion_of_register(obj, result)
    standard_used(obj, result)
    number_of_articles(obj, result)
    journal_title(obj, result)
    supplement_of_volume(obj, result)
    sponsor(obj, result)
    journal_iso_short_title(obj, result)
    check_marking_done(obj, result)
    journal_parallel_titles(obj, result)
    medline_titles(obj, result)
    publisher(obj, result)
    order_of_register_in_database_of_issues(obj, result)
    order_by_type_of_register(obj, result)
    type_of_register(obj, result)
    field_of_use_of_system(scielo_journal, obj, result)
    journal_acron(scielo_journal, result)
    status_processing(obj, result)
    
    return result

def path_to_base_issue(obj, result):
    """
    Path to base issue
    """
    return add_to_result("v4", f"v{obj.volume}n{obj.number}", result)

def short_title(obj, result):
    """
    Short tile of the journal
    """
    return add_to_result("v30", obj.journal.short_title, result)

def volume(obj, result):
    """
    Number of the volume
    """
    return add_to_result("v31", obj.volume, result)

def number(obj, result):
    """
    Number of the issue
    """
    return add_to_result("v32", obj.number, result)

def issue_title(obj, result):
    """
    Title of the issue
    """
    return add_items("v33", [title for title in obj.issue_title.all()], result)

def part(obj, result):
    """
    Part
    """
    return result["v34"].append({"_": None})

def issn(scielo_journal, result):
    """
    ISSN
    """
    return add_to_result("v35", scielo_journal.issn_scielo, result)

def title_of_issue(obj, result):
    """
    Title of the issue
    """
    return add_to_result("v36", f"{obj.year}{obj.number}", result)

def status_issue(obj, result):
    """
    Status issue
    """
    return add_to_result("v42", '1', result)

def legend_bibliographic(obj, result):
    """
    Legend bibliographic
    ex:
    [
        {
            'l': 'pt', 
            'c': 'São Paulo', 
            't': 'Rev Odontol Univ São Paulo', 
            'v': 'v. 11', 
            'n': 'n. 2', 
            'm': 'Abr./Jun.', 
            '': '', 
            'a': '1997'
        }, 
        {
            'l': 'en', 
            'c': 'São Paulo', 
            't': 'Rev Odontol Univ São Paulo', 
            'v': 'vol. 11', 
            'n': 'no. 2', 
            'm': 'Apr./June', 
            '': '', 
            'a': '1997'
        }, 
        {
            'l': 'es', 
            'c': 'São Paulo', 
            't': 'Rev Odontol Univ São Paulo', 
            'v': 'v. 11', 
            'n': 'n. 2', 
            'm': 'Abr./Jun.', 
            '_': '', 
            'a': '1997'
        }
    ]
    """
    city = obj.journal.location.city.name if obj.journal.location and obj.journal.location.city else None
    journal_title = obj.journal.title if obj.journal and obj.journal.title else None

    volume_info = {
        'pt': f"v. {obj.volume}",
        'es': f"v. {obj.volume}",
        'en': f"vol. {obj.volume}"
    }
    number_info = {
        'pt': f"n. {obj.number}",
        'es': f"n. {obj.number}",
        'en': f"no. {obj.number}"
    }

    v43_entries = [
        {
            'l': lang,
            't': journal_title,
            'c': city,
            'v': volume_info[lang],
            'n': number_info[lang],
            'a': obj.year,
            'm': obj.season,
            '': '',
        }
        for lang in ['pt', 'es', 'en']
    ]

    return result["v43"].extend(v43_entries)


def title_summary(obj, result):
    """"
    Title of the "Summary" (title)
    """
    return result['v48'].append({'h': 'Sumário', 'l': 'pt', '_': ''}, {'h': 'Table of Contents', 'l': 'en', '_': ''}, {'h': 'Sumario', 'l': 'es', '_': ''})

def editora(obj, result):
    """
    Editora
    """
    return add_items("v62", [ch.get_institution_name for ch in obj.journal.copyright_holder_history.all()], result)

def publication_date(obj, result):
    """
    Publication date of the issue
    """
    year = obj.year
    month = obj.month
    if year and month:
        return result["v64"].append({"a": year, "m": month})
    elif year:
        return result["v64"].append({"a": year})
    
def publication_date_normalized(obj, result):
    """
    Publication date of the issue normalized
    """
    year = obj.year
    month = obj.month
    if year and month:
        return add_to_result("v65", year + month + '00', result)
    elif year:
        return add_to_result("v65", year + '0000', result)

def vocabulary_control(obj, result):
    """
    vocabulary control
    """
    if obj.journal and obj.journal.vocabulary:
        return add_to_result("v85", obj.journal.vocabulary.acronym, result)

def date_of_inclusion_of_register(obj, result):
    """
    Date of inclusion of register
    """
    return add_to_result("v91", obj.created.strftime("%Y-%m-%d"), result)

def standard_used(obj, result):
    """
    Standard used
    """
    return add_to_result("v117", obj.journal.standard.code if obj.journal.standard else None, result)

def number_of_articles(obj, result):
    """
    Number of articles
    """
    return add_to_result("v122", Article.objects.count(), result)

def journal_title(obj, result):
    """
    Title of the journal
    """
    return add_to_result("v130", obj.journal.title if obj.journal.title else None, result)

def supplement_of_volume(obj, result):
    """
    Supplement of volume and number
    """
    if not obj.number:
        return add_to_result("v131", obj.supplement, result)
    return add_to_result("v132", obj.supplement, result)

def sponsor(obj, result):
    """
    Sponsor of the journal
    """
    return add_items("v140", [sponsor.get_institution_name for sponsor in obj.journal.sponsor_history.all()], result)

def journal_iso_short_title(obj, result):
    """
    ISO short title of the journal
    """
    return add_to_result("v151", obj.journal.official.iso_short_title if obj.journal.official and obj.journal.official.iso_short_title else None, result)

def check_marking_done(obj, result):
    return add_to_result("v200", '0', result)

def journal_parallel_titles(obj, result):
    """
    Journal parallel titles
    """
    return add_items("v230", [pt.text for pt in obj.journal.official.parallel_titles if obj.journal.official and pt.text], result)

def medline_titles(obj, result):
    """
    Medline titles
    """
    medline_titles = TitleInDatabase.objects.filter(journal=obj.journal, indexed_at__acronym__iexact="medline")
    return add_items("v421", [medline.title for medline in medline_titles], result)

def publisher(obj, result):
    """
    Publisher
    """
    return add_items("v480", [publisher.get_institution_name for publisher in obj.journal.publisher_history.all()], result)

def order_of_register_in_database_of_issues(obj, result):
    """
    Order of register in database of issues
    """
    return add_to_result("700", '0', result)

def order_by_type_of_register(obj, result):
    """
    Order by type of register
    """
    return add_to_result("701", '1', result)

def type_of_register(obj, result):
    """
    Type of register
    """
    return add_to_result("706", 'i', result)

def field_of_use_of_system(scielo_journal, obj, result):
    """
    Field of use of system
    """
    return add_to_result("v888", f"{scielo_journal.journal_acron.upper()}{obj.volume}{obj.number}", result)

def journal_acron(scielo_journal, result):
    """
    Journal acron
    """
    return add_to_result("v930", scielo_journal.journal_acron, result)

def status_processing(obj, result):
    """
    Status processing
    """
    return add_to_result("v991", '1', result)