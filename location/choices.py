regions = (
    ("", ""),
    ("Norte", "Norte"),
    ("Nordeste", "Nordeste"),
    ("Centro-Oeste", "Centro-Oeste"),
    ("Sudeste", "Sudeste"),
    ("Sul", "Sul"),
)

# Processing status for canonical location data
LOCATION_STATUS = (
    ("RAW", "RAW"),  # Raw data, no processing
    ("CLEANED", "CLEANED"),  # Pre-cleaned data
    ("MATCHED", "MATCHED"),  # Matched to canonical record
    ("VERIFIED", "VERIFIED"),  # Officially validated
    ("REJECTED", "REJECTED"),  # Invalid or unresolvable
)
