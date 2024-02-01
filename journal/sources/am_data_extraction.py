import logging


def get_issns(
    issn_print_or_electronic,
    issn_scielo,
    type_issn,
    current_issn,
):
    if issn_print_or_electronic:
        return extract_issn_print_electronic(issn_print_or_electronic)

    type_ = None
    if type_issn:
        for item in type_issn:
            try:
                type_ = item.get("_")
            except KeyError:
                pass
    if type_:
        if current_issn:
            issn = extract_value(current_issn)
        elif issn_scielo:
            issn = issn_scielo
        logging.info((current_issn, issn_scielo, type_issn, type_, issn))
        return extract_issn_print_electronic([{'t': type_, '_': issn}])
    return None, None


def extract_issn_print_electronic(issn_print_or_electronic):
    """
    issn_print_or_electronic:
        [{'t': 'ONLIN', '_': '1677-9487'}], [{'t': 'PRINT', '_': '0034-7299'}]
    """
    issn_print = None
    issn_electronic = None

    if issn_print_or_electronic:
        for issn in issn_print_or_electronic:
            if issn.get("t") == "PRINT":
                issn_print = issn.get("_").strip()
            elif issn.get("t") == "ONLIN":
                issn_electronic = issn.get("_").strip()
    return issn_print, issn_electronic


def extract_value(value):
    if value and isinstance(value, list):
        if len(value) > 1:
            return [x.get("_") for x in value]
        return [x.get("_") for x in value][0]


def extract_value_mission(mission):
    """
    [
        {
            "l": "es",
            "_": "La RAE-eletr\u00f4nica tiene como misi\u00f3n fomentar la producci\u00f3n y la diseminaci\u00f3n del conocimiento en Administraci\u00f3n de Empresas."
        },
        {
            "l": "pt",
            "_": "A RAE-eletr\u00f4nica tem como miss\u00e3o fomentar a produ\u00e7\u00e3o e a dissemina\u00e7\u00e3o de conhecimento em Administra\u00e7\u00e3o de Empresas."
        },
        {
            "l": "en",
            "_": "RAE-eletr\u00f4nica's mission is to encourage the production and dissemination of Business Administration knowledge."
        }
    ]
    """

    return [{"lang": x.get("l"), "mission": x.get("_")} for x in mission]


def parse_date_string(date):
    """
    Exemplos de date:
        '20121200', '2002', '20130000' e None
    """
    year = None
    month = None
    if date:
        if date.isdigit() and len(date) == 4:
            year = date
            month = None
        elif date.isdigit and len(date) == 8:
            year = date[0:4]
            month = date[4:6] if date[4:6] != "00" else None
    return year, month


def extract_value_from_journal_history(value):
    """
    https://articlemeta.scielo.org/api/v1/journal/?collection=scl&issn=0100-8455
    https://articlemeta.scielo.org/api/v1/journal/?collection=scl&issn=0100-1965
    Ex value:
        [
            {'c': '20120600', 'b': 'C', 'a': '20080000', 'd': 'S', '_': '', 'e': 'suspended-by-committee'},
            {'c': '20030000', 'b': 'C', 'a': '19991216', 'd': 'S', '_': '', 'e': 'suspended-by-committee'}
        ]
    """
    data = []
    if value:
        for v in value:
            initial_year, initial_month = parse_date_string(v.get("a"))
            final_year, final_month = parse_date_string(v.get("c"))
            data.append(
                {
                    "initial_year": initial_year,
                    "initial_month": initial_month,
                    "final_year": final_year,
                    "final_month": final_month,
                    "event_type": v.get("d"),
                    "interruption_reason": v.get("e"),
                }
            )
        return data
