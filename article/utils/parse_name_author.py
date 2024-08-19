import re


def parse_author_name(name):
    # Usando regex para encontrar os padrões de nome/sobrenome
    name_pattern = re.compile(r"^\s*([^,]+)\s*,\s*(.+?)\s*$")
    match = name_pattern.match(name)

    if match:
        return {"given_names": match.group(2), "surname": match.group(1)}
    else:
        return {"declared_name": name}
