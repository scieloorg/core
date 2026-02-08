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

LOGO_PURPOSE = [
    ("homepage", _("Homepage")),
    ("header", _("Header")),
    ("logo_drop_menu", _("Logo drop menu")),
    ("footer", _("Footer")),
    ("menu", _("Menu")),
]

PLATFORM_STATUS = [
    ("classic", _("Classic")),
    ("new", _("New")),
    ("migrating", _("Migrating")),
]