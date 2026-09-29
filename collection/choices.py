from django.utils.translation import gettext_lazy as _

STATUS = [
    ("certified", _("Certified")),
    ("development", _("Development")),
    ("diffusion", _("Diffusion")),
    ("independent", _("Independent")),
]

TYPE = [
    ("journals", _("Journals")),
    ("preprints", _("Preprints")),
    ("repositories", _("Repositories")),
    ("books", _("Books")),
    ("data", _("Data repository")),
]
PLATFORM_STATUS = [
    ("classic", _("Classic")),
    ("new", _("New")),
    ("migrating", _("Migrating")),
    ("migrated", _("Migrated")),
]
NETWORK_CLASSIFICATION = [
    ("scielonetwork", _("SciELO Network")),
    ("thematic", _("Thematic")),
    ("independent", _("Independent")),
]
