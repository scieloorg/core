from django.utils.translation import gettext as _

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
