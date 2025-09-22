def add_items(key, items, dictonary, field_name="_"):
    for item in items:
        add_to_result(key, item, dictonary, field_name)


def add_to_result(key, value, dictonary, field_name="_"):
    if value:
        if key not in dictonary:
            dictonary[key] = []
        dictonary[key].append({field_name: value})


def add_multiple_to_result(dict_with_values, dictonary, field_name="_"):
    for key, value in dict_with_values.items():
        add_to_result(key, value, dictonary, field_name)
