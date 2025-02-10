def add_items(key, items, dictonary):
    for item in items:
        add_to_result(key, item, dictonary)

def add_to_result(key, value, dictonary):
    if value:
        if key not in dictonary:
            dictonary[key] = []
        dictonary[key].append({"_": value})
