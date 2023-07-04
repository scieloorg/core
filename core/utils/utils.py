import re
from langcodes import tag_is_valid, standardize_tag


def language_iso(code):
    code = re.split(r"-|_", code)[0] if code else ""
    if tag_is_valid(code):
        return standardize_tag(code)
    return ""