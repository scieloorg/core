def _get_digits(value):
    if value is None:
        return 0
    if isinstance(value, int):
        return int(value)
    s = str(value)
    digits = "".join([c for c in s if c.isdigit()])
    return int(digits) if digits else 0