import re

def extracts_normalized_email(raw_email):
    if raw_email:
        email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw_email.replace(" ", ""))
        if email_match:
            return email_match.group()
    return None