def add_items(key, items, dictonary, field_name="_"):
    for item in items:
        add_to_result(key, item, dictonary, field_name)

def add_to_result(key, value, dictonary, field_name="_"):
    if value:
        dictonary[key].append({field_name: value})
