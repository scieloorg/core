"""
Utility functions for researcher-related operations.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ORCID format regex - accepts URLs or just the ID
ORCID_REGEX = re.compile(
    r"\b(?:https?://)?(?:www\.)?(?:orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])\b"
)


def clean_orcid(orcid_input):
    """
    Clean and validate ORCID identifier.
    
    This function:
    - Strips URL prefixes (http://, https://orcid.org/, etc.)
    - Validates the ORCID format using ORCID_REGEX
    - Returns the cleaned ORCID in format XXXX-XXXX-XXXX-XXXX
    
    Args:
        orcid_input: Raw ORCID input (may include URL or just the ID)
        
    Returns:
        Cleaned ORCID in format XXXX-XXXX-XXXX-XXXX or None if input is empty
        
    Raises:
        ValidationError: If ORCID format is invalid
        
    Examples:
        >>> clean_orcid("https://orcid.org/0000-0001-2345-6789")
        "0000-0001-2345-6789"
        >>> clean_orcid("0000-0001-2345-6789")
        "0000-0001-2345-6789"
    """
    if not orcid_input:
        return None
    
    # Try to match and extract ORCID using the regex
    match = ORCID_REGEX.match(orcid_input.strip())
    if match:
        # Extract the ORCID ID (group 1 from the regex)
        return match.group(1)
    
    # If no match, raise validation error
    raise ValidationError(
        _("Invalid ORCID format: %(orcid)s. Expected format: 0000-0000-0000-0000") % {'orcid': orcid_input}
    )


def extract_orcid_number(orcid):
    """
    Extract the ORCID number from ORCID input (URL or ID).
    
    This is an alias for clean_orcid for backward compatibility.
    
    Args:
        orcid: ORCID input (may include URL)
        
    Returns:
        ORCID in format XXXX-XXXX-XXXX-XXXX
    """
    return clean_orcid(orcid)
