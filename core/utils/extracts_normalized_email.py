import re


def extracts_normalized_email(raw_email):
    """
    Extracts and normalizes an email address from a given raw string.

    This function uses a regular expression to identify and extract a valid
    email address from the provided input string. It removes any spaces
    from the raw string before processing. If no valid email is found,
    the function returns None.

    Args:
        raw_email (str): A string containing the raw email data. This may
                         include extra characters, spaces, or invalid formatting.

    Returns:
        str or None: The normalized email address if found, otherwise None.

    Example:
        >>> extracts_normalized_email('   user@example.com ')
        'user@example.com'
        >>> extracts_normalized_email('<a href="mailto:user@example.com">user@example.com</a>')
        'user@example.com'
        >>> extracts_normalized_email('invalid-email.com')
        None
        >>> extracts_normalized_email('lto:user@example.com">user@example.com</a>')
        'user@example.com'
    """
    if raw_email:
        email_match = re.search(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            raw_email.replace(" ", ""),
        )
        if email_match:
            return email_match.group()
    return None
