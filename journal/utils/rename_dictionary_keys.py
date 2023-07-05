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