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

    separators = get_separators(text_)

    # padroniza a quantidade de espaços
    text_ = " ".join([item.strip() for item in text_.split() if item.strip()])
    for sep in separators:
        text_ = text_.replace(sep, "#####")

    return [item.strip() for item in text_.split("#####") if item.strip()]


def standardize_acronym_and_name(
    original, possible_multiple_return=None, q_locations=None
):
    """
    Dado o texto original, identifica pares de acrônimo e nome.
    Os separadores podem separar acrônimo e nome e/ou itens de lista.
    Ex.: USP / Unicamp
    São Paulo/SP, Rio de Janeiro/RJ

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

    if possible_multiple_return:
        yield from standardize_acronym_and_name_multiple(
            splitted_text,
            acrons,
            names,
            original,
            q_locations,
        )
    yield standardize_acronym_and_name_one(splitted_text, acrons, names)


def standardize_acronym_and_name_one(splitted_text, acrons, names):
    """
    Dado o texto original, identifica pares de acrônimo e nome.
    Os separadores podem separar acrônimo e nome e/ou itens de lista.
    Ex.: USP / Unicamp
    São Paulo/SP, Rio de Janeiro/RJ

    """

    if acrons and not names:
        for acron in acrons:
            return {"acronym": acron}

    if names and not acrons:
        for name in names:
            return {"name": name}

    if len(names) == len(acrons):
        match = None
        for acron, name in zip(acrons, names):
            if name.startswith(acron[0]):
                match = True
            else:
                match = False
                break
        if match:
            for acron, name in zip(acrons, names):
                return {"acronym": acron, "name": name}
        else:
            return name_and_divisions(splitted_text)

    if len(acrons) == 1 and len(names) > 1:
        acron = acrons[0]
        if names[0].startswith(acron[0]):
            d = {"acronym": acron}
            splitted_text.remove(acron)
            d.update(name_and_divisions(splitted_text))
            return d

    # retorna o original
    return name_and_divisions(splitted_text)


def standardize_acronym_and_name_multiple(
    splitted_text,
    acrons,
    names,
    original,
    q_locations,
):
    """
    Dado o texto original, identifica pares de acrônimo e nome.
    Os separadores podem separar acrônimo e nome e/ou itens de lista.
    Ex.: USP / Unicamp
    São Paulo/SP, Rio de Janeiro/RJ

    Parameters
    ----------
    possible_multiple_return : boolean
    q_locations : int
        indica se é esperado 1 instituição ou várias

    """
    if acrons and not names:
        for acron in acrons:
            yield {"acronym": acron}

    if names and not acrons:
        for name in names:
            yield {"name": name}

    if len(names) == len(acrons):
        match = None
        for acron, name in zip(acrons, names):
            if name.startswith(acron[0]):
                match = True
            else:
                match = False
                break
        if match:
            for acron, name in zip(acrons, names):
                yield {"acronym": acron, "name": name}
        else:
            if q_locations == 1:
                yield name_and_divisions(splitted_text)
            else:
                for item in splitted_text:
                    yield {"name": item}

    if len(acrons) == 1 and len(names) > 1:
        acron = acrons[0]
        if names[0].startswith(acron[0]):

            if q_locations == 1:
                d = {"acronym": acron}
                splitted_text.remove(acron)
                d.update(name_and_divisions(splitted_text))
                yield d
            else:
                yield {"acronym": acron, "name": names[0]}
                for item in names[1:]:
                    yield {"name": item}
        else:
            if q_locations == 1:
                yield name_and_divisions(splitted_text)
            else:
                for item in splitted_text:
                    yield {"name": item}
    else:
        if q_locations == 1:
            yield name_and_divisions(splitted_text)
        else:
            for item in splitted_text:
                yield {"name": item}


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
