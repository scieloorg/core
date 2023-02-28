import hashlib


def generate_finger_print(content):
    if not content:
        return None
    if isinstance(content, str):
        content = content.upper()
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def get_file_finger_print(source_filename):
    with open(source_filename, "rb") as fp:
        return generate_finger_print(fp.read())
