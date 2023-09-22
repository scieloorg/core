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
