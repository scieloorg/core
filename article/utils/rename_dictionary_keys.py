correspondencia_journal = {
    "v5": "type_of_literature",
    "v6": "treatment_level",
    "v10": "center_code",
    "v20": "national_code",
    "v30": "identification_number",
    "v35": "issn_type",
    "v37": "secs_code",
    "v50": "publication_status",
    "v51": "journal_status_history_in_this_collection",
    "v62": "copyright_holder",
    "v63": "address",
    "v64": "electronic_address",
    "v66": "ftp",
    "v67": "user_subscription",
    "v68": "acronym",
    "v69": "url_of_the_journal",
    "v85": "controled_vocabulary",
    "v90": "notes",
    "v100": "publication_title",
    "v110": "subtitle",
    "v117": "standard",
    "v130": "section",
    "v140": "sponsor",
    "v150": "short_title",
    "v151": "iso_short_title",
    "v230": "parallel_titles",
    "v240": "other_titles",
    "v301": "initial_date",
    "v302": "initial_volume",
    "v303": "initial_number",
    "v304": "terminate_date",
    "v305": "final_volume",
    "v306": "final_number",
    "v310": "publisher_country",
    "v320": "publisher_state",
    "v330": "level_of_publication",
    "v340": "alphabet",
    "v350": "text_idiom",
    "v360": "abstract_language",
    "v380": "frequency",
    "v400": "issn_id",
    "v420": "medline_code",
    "v421": "medline_short_title",
    "v430": "classification",
    "v435": "issn",
    "v440": "subject_descriptors",
    "v441": "study_area",
    "v450": "indexing_coverage",
    "v480": "publisher",
    "v490": "publisher_city",
    "v540": "identifying_regular_issues",
    "v550": "has_supplement",
    "v541": "license_of_use",
    "v560": "is_supplement",
    "v610": "old_title",
    "v690": "url_of_the_main_collection",
    "v691": "scielo_net",
    "v692": "url_of_submission_online",
    "v699": "publishing_model",
    "v710": "new_title",
    "v851": "web_of_knowledge_databases",
    "v852": "web_of_knowledge_databases",
    "v853": "web_of_knowledge_databases",
    "v854": "subject_categories",
    "v900": "notes",
    "v901": "mission",
    "v930": "acronym_lowercase_and_or_uppercase_letters",
    "v935": "current_issn",
    "v940": "creation_date",
    "v941": "update_date",
    "v950": "documentalist_creation",
    "v951": "documentalist_update",
}

correspondencia_issue = {
    "v31": "volume",
    "v32": "number",
    'v33': 'issue_title',
    'v34': 'part',
    'v35': 'scielo_issn',
    'v42': 'status',
    "v43": "bibliographic_strip",
    'v48': 'header_of_table_of_contents',
    'v49': 'sections_data',
    'v62': 'issue_editor',
    'v65': 'date_iso',
    'v85': 'controlled_vocabulary',
    'v97': 'cover',
    'v117': 'standard',
    'v122': 'number_of_documents',
    "v131": "supllement",
    "v132": "supllement",
    'v140': 'sponsor',
    'v200': 'markup_done',
    'v435': 'issn',
    'v540': 'identifying_regular_issues'
}

def rename_dictionary_keys(dictionary, corresp):
    """
    Renomeia as chaves de um dicionário com base em um dicionário de correspondência.

    O dicionário de correspondência contém os valores das chaves obtidos em:
    - https://scielo.readthedocs.io/projects/scielo-pc-programs/en/latest/titlemanager_title.html
    - https://scielo.readthedocs.io/projects/scielo-pc-programs/en/latest/titlemanager_issue.html

    Args:
        dictionary (dict): Dicionário.

    Returns:
        dict: Um novo dicionário com as chaves atualizadas de acordo com o dicionário de correspondência.
    """

    return {corresp[key] if key in corresp else key: dictionary[key] for key in dictionary}