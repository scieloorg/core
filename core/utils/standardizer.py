import logging


ITEMS_SEP_FOR_LOCATION = [";", ", ", "|", "/"]
PARTS_SEP_FOR_LOCATION = [" - ", "- ", " -", ", ", "(", "/"]

ITEMS_SEP_FOR_CITY = [",", "|"]
PARTS_SEP_FOR_CITY = []


def remove_extra_spaces(text):
    text = text and text.strip()
    if not text:
        return text
    # padroniza a quantidade de espaços
    return " ".join([item.strip() for item in text.split() if item.strip()])


def standardize_code_and_name(original):
    """
    Dado o texto original, identifica pares de code e nome.
    Os separadores podem separar code e nome e/ou itens de lista.
    Ex.: USP / Unicamp
    São Paulo/SP, Rio de Janeiro/RJ
    """
    text_ = original
    text_ = text_ and text_.strip()
    if not text_:
        return []

    text_ = remove_extra_spaces(text_)
    if not text_:
        yield {"name": None}
        return

    items_separators = ITEMS_SEP_FOR_LOCATION
    parts_separators = PARTS_SEP_FOR_LOCATION

    PARTBR = "~PARTBR~"
    LINEBR = "~LINEBR~"
    for sep in items_separators:
        text_ = text_.replace(sep, PARTBR)
    for sep in parts_separators:
        text_ = text_.replace(sep, PARTBR)

    codes = []
    names = []
    for item in text_.split(PARTBR):
        item = item.strip()
        if not item:
            continue
        if len(item) == 2:
            codes.append(item)
        else:
            names.append(item)

    if len(names) == len(codes):
        for acron, name in zip(codes, names):
            yield {"code": acron, "name": name}
    elif len(names) == 0:
        for acron in codes:
            yield {"code": acron}
    elif len(codes) == 0:
        for name in names:
            yield {"name": name}
    else:
        # como o texto está bem fora do padrão,
        # pode-se evidenciar retornando o original
        yield {"name": original}


def standardize_name(original):
    original = original and original.strip()
    if not original:
        return

    items_separators = ITEMS_SEP_FOR_CITY

    LINEBR = "~LINEBR~"

    text_ = original
    text_ = remove_extra_spaces(text_)

    for sep in items_separators:
        text_ = text_.replace(sep, LINEBR)

    for row in text_.split(LINEBR):
        row = row and row.strip()
        if not row:
            continue
        yield {"name": row}
