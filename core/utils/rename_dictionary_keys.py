correspondencia = {
    "v5": "type_of_literature",
    "v6": "treatment_level",
    "v10": "center_code",
    "v20": "national_code",
    "v30": "identification_number",
    "v33": "issues_title",
    "v34": "part",
    "v37": "secs_code",
    "v42": "status",
    "v48": "header_of_table_of_contents",
    "v49": "sections_data",
    "v50": "publication_status",
    "v51": "journals_status_history_in_this_collection",
    "v51abcd": "journal_history",
    "v62": "issue_editor",
    "v63": "address",
    "v64": "electronic_address",
    "v65": "date_iso",
    "v66": "ftp",
    "v67": "user_subscription",
    "v68": "acronym",
    "v69": "url_of_the_journal",
    "v85": "controlled_vocabulary",
    "v97": "cover",
    "v100": "publication_title",
    "v110": "subtitle",
    "v117": "standard",
    "v122": "number_of_documents",
    "v130": "section",
    "v140": "sponsor",
    "v150": "short_title",
    "v151": "iso_short_title",
    "v200": "markup_done",
    "v230": "parallel_titles",
    "v240": "other_titles",
    "v301": "initial_date",
    "v302": "initial_volume",
    "v303": "initial_number",
    "v304": "terminate_date",
    "v305": "final_volume",
    "v306": "final_number",
    "v310": "publishers_country",
    "v320": "publishers_state",
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
    "v490": "publishers_city",
    "v540tl": "text_provided_by_creative_commons_site_according_to_the_license_choice",
    "v550": "has_supplement",
    "v560": "is_supplement",
    "v610": "old_title",
    "v691": "scielo_net",
    "v690": "url_of_the_main_collection",
    "v692": "url_of_submission_online",
    "v699": "publishing_model",
    "v710": "new_title",
    "v851": "web_of_knowledge_databases",
    "v852": "web_of_knowledge_databases",
    "v853": "web_of_knowledge_databases",
    "v854": "subject_categories",
    "v900": "notes",
    "v901": "mission",
    "v930": "acronym_lowercase_uppercase_letters)",
    "v940": "creation_date",
    "v941": "update_date",
    "v950": "documentalist_creation",
    "v951": "documentalist_update"
}

def rename_dictionary_keys(dictionary):
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
    return {correspondencia[key] if key in correspondencia else key: dictionary[key] for key in dictionary}