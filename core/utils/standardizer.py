def get_separators(text, exclusion_list=None):
    exclusion_list = exclusion_list or '.-!@#$%&"' + "'"
    separators = []
    for c in text:
        if c.isalnum() or c in exclusion_list:
            continue
        if c.strip():
            separators.append(c)
    return separators


def get_splitted_text(text):
    text = text and text.strip()
    if not text:
        return []

    text_ = text.replace(" - ", "/").replace("- ", "/").replace(" -", "/")
    text_ = text_.replace(". ", "/")
    text_ = remove_extra_spaces(text_)

    separators = get_separators(text_)

    for sep in separators:
        text_ = text_.replace(sep, "#####")

    return [item.strip() for item in text_.split("#####") if item.strip()]


def remove_extra_spaces(text):
    # padroniza a quantidade de espaços
    if text is None:
        return None
    elif not isinstance(text, str):
        raise TypeError("The argument must be a string or list")
    
    return " ".join([item.strip() for item in text.split() if item.strip()])


def standardize_acronym_and_name(
    original, possible_multiple_return=None, q_locations=None
):
    """
    Dado o texto original, identifica pares de acrônimo e nome,
    ou lista de acrônimos ou lista de nomes.
    Retorna um ou mais itens dependendo do valor de q_locations que
    deve ser correspondente à quantidade de itens identificados,
    caso contrário, retornará `{"name": original}

    Parameters
    ----------
    possible_multiple_return : boolean
    q_locations : int
        indica se é esperado 1 instituição ou várias

    """
    splitted_text = get_splitted_text(original)
    acrons = []
    names = []

    for value in splitted_text:
        if " " in value:
            names.append(value)
        elif value.upper() == value:
            # acrônimos nao tem espaco no nome,
            # mas podem ter combinações de maiúsculas e minúsculas
            acrons.append(value)
        else:
            if value[1:].lower() == value[1:]:
                names.append(value)
            else:
                acrons.append(value)

    if possible_multiple_return and q_locations and q_locations > 1:
        yield from standardize_acronym_and_name_multiple(
            splitted_text,
            acrons,
            names,
            original,
            q_locations,
        )
    else:
        yield standardize_acronym_and_name_one(splitted_text, acrons, names, original)


def standardize_acronym_and_name_one(splitted_text, acrons, names, original):
    """
    Retorna um par acron e name ou somente um name ou somente um acron,
    caso contrário retorna `{"name": original}`
    """
    original = remove_extra_spaces(original)
    if acrons and not names:
        if len(acrons) > 1:
            return {"name": original}

    if names and not acrons:
        if len(names) > 1:
            return name_and_divisions(splitted_text)

    if len(names) == len(acrons) == 1:
        for acron, name in zip(acrons, names):
            if name.startswith(acron[0]):
                return {"acronym": acron, "name": name}
            else:
                return {"name": original}

    if len(acrons) == 1 and len(names) > 1:
        acron = acrons[0]
        if names[0].startswith(acron[0]):
            d = {"acronym": acron}
            splitted_text.remove(acron)
            d.update(name_and_divisions(splitted_text))
            return d
        else:
            return {"name": original}
    # retorna o original
    return {"name": original}


def standardize_acronym_and_name_multiple(
    splitted_text,
    acrons,
    names,
    original,
    q_locations,
):
    """
    Retorna os pares acron e name ou somente names ou somente acrons,
    mas somente se a quantidade está coerente com q_locations,
    caso contrário retorna `{"name": original}`
    """
    original = remove_extra_spaces(original)

    if acrons and not names:
        if q_locations == len(acrons):
            for acron in acrons:
                yield {"acronym": acron}
        return

    if names and not acrons:
        if q_locations == len(names):
            for name in names:
                yield {"name": name}
        return

    match = False
    if len(names) == len(acrons) == q_locations:
        for acron, name in zip(acrons, names):
            yield {"acronym": acron, "name": name}

    elif q_locations == len(splitted_text):
        for item in splitted_text:
            yield {"name": item}
    else:
        yield {"name": original}


def name_and_divisions(splitted_text):
    keys = ("name", "level_1", "level_2", "level_3")
    d = {}
    for k, v in zip(keys, splitted_text):
        d[k] = v
    return d


def standardize_code_and_name(original):
    """
    Dado o texto original, identifica pares de code e nome.
    Os separadores podem separar code e nome e/ou itens de lista.
    Ex.: USP / Unicamp
    São Paulo/SP, Rio de Janeiro/RJ
    """
    original = remove_extra_spaces(original)

    splitted_text = get_splitted_text(original)
    codes = []
    names = []
    for value in splitted_text:
        if value.upper() == value and len(value) == 2:
            # codes em maíscula
            codes.append(value)
        else:
            names.append(value)
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
    splitted_text = get_splitted_text(original)
    for item in splitted_text:
        item = item and item.strip()
        if item:
            yield {"name": item}
