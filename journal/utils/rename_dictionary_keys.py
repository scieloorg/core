def rename_dictionary_keys(dictionary, corresp):
    """
    Renomeia as chaves de um dicionário com base em um dicionário de correspondência.

    Args:
        dictionary (dict): Dicionário.

    Returns:
        dict: Um novo dicionário com as chaves atualizadas de acordo com o dicionário de correspondência.
    """

    return {corresp[key] if key in corresp else key: dictionary[key] for key in dictionary}