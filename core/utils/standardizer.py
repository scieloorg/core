import logging

ITEMS_SEP_FOR_LOCATION = [";", ", ", "|", "/"]
PARTS_SEP_FOR_LOCATION = [" - ", "- ", " -", ", ", "(", "/"]

ITEMS_SEP_FOR_CITY = [",", "|"]
PARTS_SEP_FOR_CITY = []


def remove_extra_spaces(text):
    if not text:
        return text
    # Padroniza a quantidade de espaços
    return " ".join(text.split())

def remove_html_tags(text):
    if not text:
        return text
    text = text.replace("<", "BREAKTAG<")
    text = text.replace(">", ">BREAKTAG")
    for part in text.split("BREAKTAG"):
        if part.startswith("<") and part.endswith(">"):
            continue
        if part.startswith("<"):
            continue
        if part.endswith(">"):
            continue
        yield part


def has_only_alpha_or_space(text):
    """ Verifica se o conteúdo do texto é válido como string, ou seja,
    não é vazio e não contém números. """
    if not text:
        return False
    parts = text.split()
    for part in parts:
        if not part.isalpha():
            return False
    return True


def clean_xml_tag_content(text, assert_string=True):
    if not text:
        return text
    text = "".join(remove_html_tags(text))
    text_ = remove_extra_spaces(text)
    if assert_string:
        if has_only_alpha_or_space(text_):
            return text_
        else:
            return None
    return text_


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
