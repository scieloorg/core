import re


def validate_orcid(orcid):
    """
    Valida um ORCID verificando formato e checksum.
    
    Args:
        orcid (str): ORCID no formato XXXX-XXXX-XXXX-XXXX
        
    Returns:
        bool: True se válido

    Raiser:
    ValueError
    """
    if not orcid or not re.match(r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$', orcid):
        raise ValueError(f"Invalid ORCID: {orcid}")
    
    # Calcula checksum (ISO 7064 MOD 11-2)
    digits = orcid.replace('-', '')[:-1]
    total = 0
    for digit in digits:
        total = (total + int(digit)) * 2
    
    remainder = total % 11
    checksum = (12 - remainder) % 11
    expected = 'X' if checksum == 10 else str(checksum)
    
    if orcid[-1] != expected:
        raise ValueError(f"Invalid ORCID: {orcid}")

    return True