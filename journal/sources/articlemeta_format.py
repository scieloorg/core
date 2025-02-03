from journal.models import SciELOJournal, TitleInDatabase

def get_articlemeta_format_title(obj):
    result = {}
    scielo_journal = SciELOJournal.objects.filter(journal=obj, collection__is_active=True).first()
    publisher_exists = obj.publisher_history.exists()

    def add_to_result(key, value):
        if value:
            result[key] = value

    add_to_result("collection", scielo_journal.collection.acron3 if scielo_journal else None)
    add_to_result("v5", [{"_": obj.type_of_literature}] if obj.type_of_literature else None)
    add_to_result("v6", [{"_": obj.treatment_level}] if obj.treatment_level else None)
    add_to_result("v10", [{"_": obj.center_code}] if obj.center_code else None)
    add_to_result("v20", [{"_": obj.national_code}] if obj.national_code else None)
    add_to_result("v30", [{"_": obj.identification_number}] if obj.identification_number else None)

    secs_code = TitleInDatabase.objects.filter(journal=obj, indexed_at__acronym__iexact="secs")
    add_to_result("v37", [{"_": sc.identifier} for sc in secs_code if sc.identifier] if secs_code.exists() else None)

    add_to_result("v50", [{"_": scielo_journal.status}] if scielo_journal and scielo_journal.status else None)
    add_to_result("v62", [{"_": ch.institution.institution.institution_identification.name} 
                            for ch in obj.copyright_holder_history.all() if ch.institution] if obj.copyright_holder_history.exists() else None)
    add_to_result("v66", [{"_": obj.ftp}] if obj.ftp else None)
    add_to_result("v67", [{"_": obj.user_subscription}] if obj.user_subscription else None)
    add_to_result("v68", [{"_": scielo_journal.journal_acron}] if scielo_journal and scielo_journal.journal_acron else None)
    add_to_result("v69", [{"_": obj.journal_url}] if obj.journal_url else None)
    add_to_result("v85", [{"_": obj.vocabulary.acronym}] if obj.vocabulary else None)
    add_to_result("v100", [{"_": obj.title}] if obj.official and obj.official.title else None)
    add_to_result("v110", [{"_": obj.subtitle}] if obj.subtitle else None)
    add_to_result("v117", [{"_": obj.standard.code}] if obj.standard and obj.standard.code else None)
    add_to_result("v130", [{"_": obj.section}] if obj.section else None)
    add_to_result("v140", [{"_": sponsor.institution.institution.institution_identification.name} 
                            for sponsor in obj.sponsor_history.all() if sponsor.institution] if obj.sponsor_history.exists() else None)
    add_to_result("v150", [{"_": obj.short_title}] if obj.short_title else None)
    add_to_result("v151", [{"_": obj.official.iso_short_title}] if obj.official and obj.official.iso_short_title else None)

    parallel_titles = [{"_": pt.text} for pt in obj.official.parallel_titles if pt.text]
    add_to_result("v230", parallel_titles if parallel_titles else None)

    add_to_result("v240", [{"_": other_title.title} for other_title in obj.other_titles.all()] if obj.other_titles.exists() else None)
    add_to_result("v301", [{"_": obj.official.initial_year}] if obj.official and obj.official.initial_year else None)
    add_to_result("v302", [{"_": obj.official.initial_volume}] if obj.official and obj.official.initial_volume else None)
    add_to_result("v303", [{"_": obj.official.initial_number}] if obj.official and obj.official.initial_number else None)
    if obj.official:
        year = obj.official.terminate_year
        month = obj.official.terminate_month
        if year and month:
            add_to_result("v304", [{"_": year + month}])
        elif year:
            add_to_result("v304", [{"_": year}])

    add_to_result("v305", [{"_": obj.official.final_volume}] if obj.official and obj.official.final_volume else None)
    add_to_result("v306", [{"_": obj.official.final_number}] if obj.official and obj.official.final_number else None)

    if publisher_exists:
        add_to_result("v310", [{"_": publisher.institution.institution.location.country.name or publisher.institution.institution.location.country.acronym} 
                                for publisher in obj.publisher_history.all() if publisher.institution and publisher.institution.institution.location and publisher.institution.institution.location.country])
        add_to_result("v320", [{"_": publisher.institution.institution.location.state.acronym or publisher.institution.institution.location.state.name} 
                                for publisher in obj.publisher_history.all() if publisher.institution and publisher.institution.institution.location and publisher.institution.institution.location.state])
        add_to_result("v480", [{"_": publisher.institution.institution.institution_identification.name}
                                for publisher in obj.publisher_history.all() if publisher.institution and publisher.institution.institution.institution_identification])
        add_to_result("v490", [{"_": publisher.institution.institution.location.city.name} 
                                for publisher in obj.publisher_history.all() if publisher.institution and publisher.institution.institution.location and publisher.institution.institution.location.city])

    add_to_result("v330", [{"_": obj.level_of_publication}] if obj.level_of_publication else None)
    add_to_result("v340", [{"_": obj.alphabet}] if obj.alphabet else None)
    add_to_result("v350", [{"_": lang.code2} for lang in obj.text_language.all()] if obj.text_language.exists() else None)
    add_to_result("v360", [{"_": lang.code2} for lang in obj.abstract_language.all()] if obj.abstract_language.exists() else None)
    add_to_result("v380", [{"_": obj.frequency}] if obj.frequency else None)

    medline_titles = TitleInDatabase.objects.filter(journal=obj, indexed_at__acronym__iexact="medline")
    if medline_titles.exists():
        v420 = [{"_": medline.identifier} for medline in medline_titles if medline.identifier]
        if v420:
            add_to_result("v420", v420)
        add_to_result("v421", [{"_": medline.title} for medline in medline_titles])

    add_to_result("v430", [{"_": obj.classification}] if obj.classification else None)

    issns = []
    if obj.official and obj.official.issn_print:
        issns.append({"_": obj.official.issn_print, "t": "PRINT"})
    if obj.official and obj.official.issn_electronic:
        issns.append({"_": obj.official.issn_electronic, "t": "ONLIN"})
    add_to_result("v435", issns if issns else None)

    add_to_result("v440", [{"_": descriptor.value} for descriptor in obj.subject_descriptor.all()] if obj.subject_descriptor.exists() else None)
    add_to_result("v441", [{"_": subject.value} for subject in obj.subject.all()] if obj.subject.exists() else None)
    add_to_result("v450", [{"_": index.name} for index in obj.indexed_at.all()] if obj.indexed_at.exists() else None)

    add_to_result("v550", [{"_": obj.has_supplement}] if obj.has_supplement else None)
    add_to_result("v560", [{"_": obj.is_supplement}] if obj.is_supplement else None)

    if obj.official and obj.official.old_title:
        add_to_result("v610", [{"_": old_title.title} for old_title in obj.official.old_title.all()])
    if obj.official and obj.official.new_title:
        add_to_result("v710", [{"_": obj.official.new_title.title}])

    add_to_result("v900", [{"_": annotation.notes} for annotation in obj.annotation.all()] if obj.annotation.exists() else None)
    add_to_result("v901", [{"l": mission.language.code2, "_": mission.get_text_pure} 
                            for mission in obj.mission.all() if mission.language and mission.get_text_pure] if obj.mission else None)

    result["v940"] = [{"_": obj.created}]
    result["v941"] = [{"_": obj.updated}]
    
    # Ordena o dicionário por chave
    return result