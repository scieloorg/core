from django.utils.translation import gettext_lazy as _

regions = (
    ("", ""),
    ("Norte", _("Norte")),
    ("Nordeste", _("Nordeste")),
    ("Centro-Oeste", _("Centro-Oeste")),
    ("Sudeste", _("Sudeste")),
    ("Sul", _("Sul")),
)

# Processing status for canonical location data
LOCATION_STATUS = (
    ("RAW", "RAW"),  # Raw data, no processing
    ("CLEANED", "CLEANED"),  # Pre-cleaned data
    ("MATCHED", "MATCHED"),  # Matched to canonical record
    ("VERIFIED", "VERIFIED"),  # Officially validated
    ("REJECTED", "REJECTED"),  # Invalid or unresolvable
)
