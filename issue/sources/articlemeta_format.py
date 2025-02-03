from journal.models import SciELOJournal, TitleInDatabase

def get_articlemeta_format_issue(obj):
    result = {}
    scielo_issn = SciELOJournal.objects.get(journal=obj.journal).issn_scielo

    def add_to_result(key, value):
        if value:
            result[key] = value

    add_to_result("v30", obj.journal.short_title if obj.journal.short_title else None)
    add_to_result("v31", obj.volume if obj.volume else None)
    add_to_result("v32", obj.number if obj.number else None)
    add_to_result("v35", scielo_issn if scielo_issn else None)
    add_to_result("v62", [{"_": ch.institution.institution.institution_identification.name} 
                            for ch in obj.journal.copyright_holder_history.all() if ch.institution] if obj.journal.copyright_holder_history.exists() else None)
    # Data de publicação do fascículo
    year = obj.year
    month = obj.month
    if year and month:
        add_to_result("v64", [{"_": year + month}])
    elif year:
        add_to_result("v64", [{"_": year}])
    add_to_result("v117", [{"_": obj.journal.standard.code}] if obj.journal.standard and obj.journal.standard.code else None)
    add_to_result("v130", obj.journal.title if obj.journal.title else None)
    add_to_result("v140", [{"_": sponsor.institution.institution.institution_identification.name} 
                            for sponsor in obj.journal.sponsor_history.all() if sponsor.institution] if obj.journal.sponsor_history.exists() else None)    
    add_to_result("v151", obj.journal.official.iso_short_title if obj.journal.official and obj.journal.official.iso_short_title else None)
    parallel_titles = [{"_": pt.text} for pt in obj.journal.official.parallel_titles if pt.text]
    add_to_result("v230", parallel_titles if parallel_titles else None)
    medline_titles = TitleInDatabase.objects.filter(journal=obj.journal, indexed_at__acronym__iexact="medline")
    if medline_titles.exists():
        add_to_result("v421", [{"_": medline.title} for medline in medline_titles])
    
    add_to_result("v480", [{"_": publisher.institution.institution.institution_identification.name}
                                for publisher in obj.journal.publisher_history.all() if publisher.institution and publisher.institution.institution.institution_identification])
    
    return result
