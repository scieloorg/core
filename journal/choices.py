from django.utils.translation import gettext_lazy as _

SOCIAL_NETWORK_NAMES = [
    ("facebook", "Facebook"),
    ("twitter", "Twitter"),
    ("journal", _("Journal URL")),
]

OA_STATUS = [
    ("", ""),
    ("diamond", "Diamond"),
    ("gold", "Gold"),
    ("hybrid", "Hybrid"),
    ("bronze", "Bronze"),
    ("green", "Green"),
    ("closed", "Closed")
]