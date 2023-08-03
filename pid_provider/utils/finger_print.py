import hashlib


def generate_finger_print(content):
    if not content:
        return None
    if isinstance(content, str):
        content = content.upper()
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()
