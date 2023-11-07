def rename_dictionary_keys(list_dictionary, corresp):
    """
    Renomeia as chaves de um dicionário com base em um dicionário de correspondência.

    Args:
        list_dictionary (list): Lista de dicionário.

    Returns:
        dict: Um novo dicionário com as chaves atualizadas de acordo com o dicionário de correspondência.
    """

    return {
        corresp[key] if key in corresp else key: dictionary[key]
        for dictionary in list_dictionary
        for key in dictionary
    }
